package dev.kervan.dpi.engine

/** JNI entry points into mobile/core (libkervan.so). Blocking: call off the main thread. */
object NativeEngine {
  init {
    System.loadLibrary("kervan")
  }

  /**
   * [service] must expose `protectFd(Int): Boolean`, `onEngineState(Int, Int)` and
   * `onEngineLog(Int, String)`. Those run on engine threads and must not call back
   * into [nativeStop] synchronously.
   */
  @JvmStatic external fun nativeStart(
    service: Any,
    tunFd: Int,
    mtu: Int,
    socksPort: Int,
    runtimeDir: String,
    desyncArgs: String,
    enableUdp: Boolean,
  ): Int

  @JvmStatic external fun nativeStop(): Int
  @JvmStatic external fun nativeState(): Int
  @JvmStatic external fun nativeStatusString(status: Int): String
}
