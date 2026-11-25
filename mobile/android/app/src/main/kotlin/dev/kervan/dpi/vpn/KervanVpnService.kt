package dev.kervan.dpi.vpn

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.net.VpnService
import android.os.Build
import android.os.ParcelFileDescriptor
import android.util.Log
import dev.kervan.dpi.MainActivity
import dev.kervan.dpi.R
import dev.kervan.dpi.engine.DesyncArgs
import dev.kervan.dpi.engine.DnsProvider
import dev.kervan.dpi.engine.EngineConfig
import dev.kervan.dpi.engine.EnginePhase
import dev.kervan.dpi.engine.NativeEngine
import java.net.InetAddress
import java.net.ServerSocket
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/**
 * Local-only VpnService: TUN -> native engine on this device. No remote server.
 * Every engine-created outbound socket goes through [protectFd]; if protection
 * fails the engine drops that connection instead of sending it into the tunnel.
 */
class KervanVpnService : VpnService() {

  /** All lifecycle work is serialised on this thread; never call native code on main. */
  private val worker = Executors.newSingleThreadExecutor { r -> Thread(r, "kervan-vpn") }
  private var tun: ParcelFileDescriptor? = null
  private var activeConfig: EngineConfig? = null

  override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
    when (intent?.action) {
      ACTION_STOP -> worker.execute { disconnect(null) }
      ACTION_START -> {
        goForeground()
        val config = EngineConfig(
          intent.getStringExtra(EXTRA_ARGS) ?: DesyncArgs.DEFAULT,
          DnsProvider.fromKey(intent.getStringExtra(EXTRA_DNS)),
        )
        worker.execute { connect(config) }
      }
      // Restarted by the system without our intent (e.g. always-on): stay off.
      else -> worker.execute { disconnect(null) }
    }
    return START_NOT_STICKY
  }

  private fun connect(config: EngineConfig) {
    if (tun != null) {
      if (config == activeConfig) return
      // Reconnect with new settings: same stop order as Disable, then start again.
      EngineStatus.log("Reconnecting with new settings…")
      teardown()
    }
    val args = config.desyncArgs
    DesyncArgs.validate(args)?.let { reason ->
      fail("Invalid strategy: $reason")
      return
    }
    EngineStatus.phase(EnginePhase.STARTING)
    EngineStatus.log("Starting local engine…")
    val pfd = try {
      Builder()
        .setSession(getString(R.string.app_name))
        .setMtu(MTU)
        .addAddress(TUN_V4, 32)
        .addRoute("0.0.0.0", 0)
        .addAddress(TUN_V6, 128)
        .addRoute("::", 0)
        .addDnsServer(config.dns.v4)
        .addDnsServer(config.dns.v6)
        .setMetered(false)
        .setConfigureIntent(mainIntent())
        .establish()
    } catch (e: Exception) {
      Log.e(TAG, "establish failed", e)
      null
    }
    if (pfd == null) {
      fail("VPN permission missing or interface could not be created.")
      return
    }
    tun = pfd
    val port = pickLoopbackPort()
    val runtimeDir = noBackupFilesDir.absolutePath
    val status = NativeEngine.nativeStart(this, pfd.fd, MTU, port, runtimeDir, args, true)
    if (status != 0) {
      val reason = NativeEngine.nativeStatusString(status)
      closeTun()
      fail("Engine did not start: $reason")
      return
    }
    activeConfig = config
    EngineStatus.phase(EnginePhase.RUNNING, activeConfig = config)
    EngineStatus.log("Engine running on 127.0.0.1:$port (args \"$args\", DNS ${config.dns.label}). Access is not verified.")
  }

  /** Stops the engine first (joins its threads), then closes the TUN. */
  private fun disconnect(error: String?) {
    val wasActive = tun != null
    if (wasActive) {
      EngineStatus.phase(EnginePhase.STOPPING)
      teardown()
    }
    if (error != null) {
      EngineStatus.phase(EnginePhase.FAILED, error)
      EngineStatus.log(error)
    } else {
      EngineStatus.phase(EnginePhase.STOPPED)
      if (wasActive) EngineStatus.log("Stopped. Normal network restored.")
    }
    stopForeground(STOP_FOREGROUND_REMOVE)
    stopSelf()
  }

  private fun fail(message: String) = disconnect(message)

  /** Engine first (joins its threads), then the TUN. */
  private fun teardown() {
    NativeEngine.nativeStop()
    closeTun()
    activeConfig = null
  }

  private fun closeTun() {
    try { tun?.close() } catch (e: Exception) { Log.w(TAG, "tun close", e) }
    tun = null
  }

  override fun onRevoke() {
    // Another VPN took over or the user revoked consent: same cleanup as Disable.
    worker.execute { disconnect("VPN permission was revoked.") }
  }

  override fun onDestroy() {
    worker.submit { if (tun != null) disconnect(null) }
    worker.shutdown()
    if (!worker.awaitTermination(5, TimeUnit.SECONDS)) {
      Log.e(TAG, "engine shutdown did not finish within 5 s")
    }
    super.onDestroy()
  }

  // ---- called from native engine threads (see kervan_jni.c) ----

  @Suppress("unused")
  fun protectFd(fd: Int): Boolean = protect(fd)

  @Suppress("unused")
  fun onEngineState(state: Int, reason: Int) {
    if (EnginePhase.fromNative(state) == EnginePhase.FAILED) {
      // Fail closed: never leave the tunnel up without a working engine.
      val why = NativeEngine.nativeStatusString(reason)
      worker.execute { if (tun != null) disconnect("Engine stopped unexpectedly ($why).") }
    }
  }

  @Suppress("unused")
  fun onEngineLog(level: Int, message: String) {
    if (level >= 2) EngineStatus.log(message)
  }

  // ---- helpers ----

  private fun pickLoopbackPort(): Int =
    ServerSocket(0, 1, InetAddress.getByName("127.0.0.1")).use { it.localPort }

  private fun mainIntent(): PendingIntent = PendingIntent.getActivity(
    this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE,
  )

  private fun goForeground() {
    val nm = getSystemService(NotificationManager::class.java)
    nm.createNotificationChannel(
      NotificationChannel(CHANNEL, getString(R.string.notif_channel), NotificationManager.IMPORTANCE_LOW),
    )
    val stop = PendingIntent.getService(
      this, 1, Intent(this, KervanVpnService::class.java).setAction(ACTION_STOP), PendingIntent.FLAG_IMMUTABLE,
    )
    val n: Notification = Notification.Builder(this, CHANNEL)
      .setSmallIcon(R.drawable.ic_stat_kervan)
      .setContentTitle(getString(R.string.app_name))
      .setContentText(getString(R.string.notif_text))
      .setOngoing(true)
      .setContentIntent(mainIntent())
      .addAction(Notification.Action.Builder(null, getString(R.string.action_disable), stop).build())
      .build()
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
      startForeground(NOTIF_ID, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_SYSTEM_EXEMPTED)
    } else {
      startForeground(NOTIF_ID, n)
    }
  }

  companion object {
    private const val TAG = "KervanVpn"
    const val ACTION_START = "dev.kervan.dpi.START"
    const val ACTION_STOP = "dev.kervan.dpi.STOP"
    const val EXTRA_ARGS = "desync_args"
    const val EXTRA_DNS = "dns"
    private const val CHANNEL = "kervan_engine"
    private const val NOTIF_ID = 1
    private const val MTU = 1500
    private const val TUN_V4 = "10.111.222.1"
    private const val TUN_V6 = "fd6b:7672::1"

    /** Starts, or reconnects a running engine when [config] differs. */
    fun start(context: Context, config: EngineConfig) {
      context.startForegroundService(
        Intent(context, KervanVpnService::class.java).setAction(ACTION_START)
          .putExtra(EXTRA_ARGS, config.desyncArgs)
          .putExtra(EXTRA_DNS, config.dns.key),
      )
    }

    fun stop(context: Context) {
      context.startService(Intent(context, KervanVpnService::class.java).setAction(ACTION_STOP))
    }
  }
}
