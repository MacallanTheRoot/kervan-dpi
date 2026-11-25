/*
 * JNI shim: converts types and forwards to the portable core. No engine logic.
 * Callbacks arrive on engine threads; they are attached to the JVM on first
 * use and detached automatically when the thread exits.
 */
#include <jni.h>
#include <android/log.h>
#include <pthread.h>
#include <string.h>

#include "kervan_engine.h"

#define TAG "KervanEngine"

static JavaVM *g_vm;
static pthread_key_t g_detach_key;
static pthread_once_t g_key_once = PTHREAD_ONCE_INIT;
static pthread_mutex_t g_lock = PTHREAD_MUTEX_INITIALIZER;
static kv_engine_t *g_engine;
static jobject g_service;          /* global ref, valid between start and stop */
static jmethodID g_protect_mid;    /* boolean protectFd(int) */
static jmethodID g_state_mid;      /* void onEngineState(int, int) */
static jmethodID g_log_mid;        /* void onEngineLog(int, String) */

static void detach_thread(void *unused)
{
    (void)unused;
    (*g_vm)->DetachCurrentThread(g_vm);
}

static void make_key(void) { pthread_key_create(&g_detach_key, detach_thread); }

static JNIEnv *env_for_thread(void)
{
    JNIEnv *env = NULL;
    jint r = (*g_vm)->GetEnv(g_vm, (void **)&env, JNI_VERSION_1_6);
    if (r == JNI_OK) {
        return env;
    }
    if (r != JNI_EDETACHED || (*g_vm)->AttachCurrentThread(g_vm, &env, NULL) != JNI_OK) {
        return NULL;
    }
    pthread_once(&g_key_once, make_key);
    pthread_setspecific(g_detach_key, (void *)1); /* non-NULL => destructor runs */
    return env;
}

static int protect_cb(void *user, int fd)
{
    (void)user;
    JNIEnv *env = env_for_thread();
    if (!env || !g_service) {
        return -1;
    }
    jboolean ok = (*env)->CallBooleanMethod(env, g_service, g_protect_mid, (jint)fd);
    if ((*env)->ExceptionCheck(env)) {
        (*env)->ExceptionClear(env);
        return -1;
    }
    return ok ? 0 : -1;
}

static void state_cb(void *user, kv_state_t state, kv_status_t reason)
{
    (void)user;
    JNIEnv *env = env_for_thread();
    if (!env || !g_service) {
        return;
    }
    (*env)->CallVoidMethod(env, g_service, g_state_mid, (jint)state, (jint)reason);
    if ((*env)->ExceptionCheck(env)) {
        (*env)->ExceptionClear(env);
    }
}

static void log_cb(void *user, kv_log_level_t level, const char *message)
{
    (void)user;
    __android_log_print(level >= KV_LOG_ERROR ? ANDROID_LOG_ERROR :
                        level == KV_LOG_WARN ? ANDROID_LOG_WARN : ANDROID_LOG_INFO,
                        TAG, "%s", message);
    JNIEnv *env = env_for_thread();
    if (!env || !g_service) {
        return;
    }
    /* NewStringUTF needs modified UTF-8; keep engine messages to ASCII. */
    char clean[512];
    size_t i = 0;
    for (; message[i] && i < sizeof(clean) - 1; i++) {
        unsigned char ch = (unsigned char)message[i];
        clean[i] = (ch >= 0x20 && ch < 0x7f) ? (char)ch : '?';
    }
    clean[i] = 0;
    jstring s = (*env)->NewStringUTF(env, clean);
    if (s) {
        (*env)->CallVoidMethod(env, g_service, g_log_mid, (jint)level, s);
        (*env)->DeleteLocalRef(env, s);
    }
    if ((*env)->ExceptionCheck(env)) {
        (*env)->ExceptionClear(env);
    }
}

JNIEXPORT jint JNI_OnLoad(JavaVM *vm, void *reserved)
{
    (void)reserved;
    g_vm = vm;
    return JNI_VERSION_1_6;
}

JNIEXPORT jint JNICALL
Java_dev_kervan_dpi_engine_NativeEngine_nativeStart(JNIEnv *env, jclass clazz, jobject service,
                                                     jint tun_fd, jint mtu, jint socks_port,
                                                     jstring runtime_dir, jstring desync_args,
                                                     jboolean enable_udp)
{
    (void)clazz;
    if (!service || !runtime_dir || !desync_args || socks_port <= 0 || socks_port > 65535) {
        return KV_ERR_INVALID_ARG;
    }
    pthread_mutex_lock(&g_lock);
    if (!g_engine) {
        kv_status_t st = kv_engine_create(&g_engine);
        if (st != KV_OK) {
            pthread_mutex_unlock(&g_lock);
            return st;
        }
    }
    if (kv_engine_state(g_engine) != KV_STATE_STOPPED || g_service) {
        pthread_mutex_unlock(&g_lock);
        return KV_ERR_BUSY;
    }
    jclass cls = (*env)->GetObjectClass(env, service);
    g_protect_mid = (*env)->GetMethodID(env, cls, "protectFd", "(I)Z");
    g_state_mid = (*env)->GetMethodID(env, cls, "onEngineState", "(II)V");
    g_log_mid = (*env)->GetMethodID(env, cls, "onEngineLog", "(ILjava/lang/String;)V");
    (*env)->DeleteLocalRef(env, cls);
    if (!g_protect_mid || !g_state_mid || !g_log_mid) {
        (*env)->ExceptionClear(env);
        pthread_mutex_unlock(&g_lock);
        return KV_ERR_INVALID_ARG;
    }
    g_service = (*env)->NewGlobalRef(env, service);

    const char *dir = (*env)->GetStringUTFChars(env, runtime_dir, NULL);
    const char *args = (*env)->GetStringUTFChars(env, desync_args, NULL);
    kv_engine_config_t cfg = { 0 };
    cfg.struct_size = sizeof(cfg);
    cfg.tun_fd = tun_fd;
    cfg.tun_mtu = (uint32_t)mtu;
    cfg.socks_port = (uint16_t)socks_port;
    cfg.runtime_dir = dir;
    cfg.desync_args = args;
    cfg.enable_udp = enable_udp ? 1 : 0;
    cfg.require_protect = 1; /* never send engine traffic back into the tunnel */
    cfg.protect_cb = protect_cb;
    cfg.state_cb = state_cb;
    cfg.log_cb = log_cb;
    kv_status_t st = dir && args ? kv_engine_start(g_engine, &cfg) : KV_ERR_NO_MEMORY;
    if (dir) (*env)->ReleaseStringUTFChars(env, runtime_dir, dir);
    if (args) (*env)->ReleaseStringUTFChars(env, desync_args, args);
    if (st != KV_OK) {
        (*env)->DeleteGlobalRef(env, g_service);
        g_service = NULL;
    }
    pthread_mutex_unlock(&g_lock);
    return st;
}

JNIEXPORT jint JNICALL
Java_dev_kervan_dpi_engine_NativeEngine_nativeStop(JNIEnv *env, jclass clazz)
{
    (void)clazz;
    pthread_mutex_lock(&g_lock);
    kv_status_t st = g_engine ? kv_engine_stop(g_engine) : KV_OK;
    /* All engine threads have joined: no callback can use g_service now. */
    if (g_service) {
        (*env)->DeleteGlobalRef(env, g_service);
        g_service = NULL;
    }
    pthread_mutex_unlock(&g_lock);
    return st;
}

JNIEXPORT jint JNICALL
Java_dev_kervan_dpi_engine_NativeEngine_nativeState(JNIEnv *env, jclass clazz)
{
    (void)env;
    (void)clazz;
    return g_engine ? (jint)kv_engine_state(g_engine) : KV_STATE_STOPPED;
}

JNIEXPORT jstring JNICALL
Java_dev_kervan_dpi_engine_NativeEngine_nativeStatusString(JNIEnv *env, jclass clazz, jint status)
{
    (void)clazz;
    return (*env)->NewStringUTF(env, kv_status_string((kv_status_t)status));
}
