cmake_minimum_required(VERSION 3.22)
project(kervan_core C ASM)

# Portable Kervan engine: our orchestrator + vendored ByeDPI + hev-socks5-tunnel.
# Run third_party/fetch.sh first. Used by the Android NDK build and host tests;
# an Apple build can reuse the same source lists.

option(KV_WITH_TUNNEL "Build hev-socks5-tunnel (TUN -> SOCKS5)" ON)
option(KV_BUILD_TESTS "Build host unit tests" OFF)

set(CMAKE_C_STANDARD 11)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(TP ${CMAKE_CURRENT_SOURCE_DIR}/third_party/src)

if(NOT EXISTS ${TP}/byedpi/proxy.c)
  message(FATAL_ERROR "Missing upstream sources: run mobile/core/third_party/fetch.sh")
endif()

# ---- ByeDPI (MIT) ----
set(BYEDPI_SRC packets.c main.c conev.c proxy.c desync.c mpool.c extend.c)
list(TRANSFORM BYEDPI_SRC PREPEND ${TP}/byedpi/)
add_library(kv_byedpi STATIC ${BYEDPI_SRC} src/kv_byedpi.c)
target_include_directories(kv_byedpi PRIVATE ${TP}/byedpi)
target_compile_definitions(kv_byedpi PRIVATE _DEFAULT_SOURCE)
target_compile_options(kv_byedpi PRIVATE -Wno-unused -Wno-unused-parameter)
# We drive ByeDPI through parse_args/init/start_event_loop; its main() is unused.
set_source_files_properties(${TP}/byedpi/main.c PROPERTIES COMPILE_DEFINITIONS "main=kv_byedpi_unused_main")
if(ANDROID)
  target_compile_definitions(kv_byedpi PRIVATE ANDROID_APP)
  target_link_libraries(kv_byedpi PRIVATE log)
endif()

set(KV_LIBS kv_byedpi)

# ---- hev-socks5-tunnel (MIT) and its pinned submodules ----
if(KV_WITH_TUNNEL)
  set(HEV ${TP}/hev-socks5-tunnel)
  set(HEV_TS ${HEV}/third-part/hev-task-system)
  set(HEV_LWIP ${HEV}/third-part/lwip)
  set(HEV_YAML ${HEV}/third-part/yaml)

  file(GLOB_RECURSE HEV_TS_SRC ${HEV_TS}/src/*.c ${HEV_TS}/src/*.S)
  add_library(kv_hev_task_system STATIC ${HEV_TS_SRC})
  target_include_directories(kv_hev_task_system PRIVATE ${HEV_TS}/src PUBLIC ${HEV_TS}/include)
  target_compile_options(kv_hev_task_system PRIVATE -fvisibility=hidden)
  target_compile_definitions(kv_hev_task_system PRIVATE
    ENABLE_STACK_OVERFLOW_DETECTION ENABLE_IO_SPLICE_SYSCALL
    CONFIG_STACK_BACKEND=STACK_MMAP CONFIG_STACK_OVERFLOW_DETECTION=1
    CONFIG_MEMALLOC_SLICE_ALIGN=16 CONFIG_MEMALLOC_SLICE_MAX_SIZE=4096
    CONFIG_MEMALLOC_SLICE_MAX_COUNT=1000 CONFIG_SCHED_CLOCK=CLOCK_NONE
    CONFIG_SCHED_IO_POLL_INTERVAL=50000)
  # Upstream Android.mk builds the task system without the slice allocator.

  file(GLOB_RECURSE HEV_LWIP_SRC ${HEV_LWIP}/src/*.c)
  add_library(kv_lwip STATIC ${HEV_LWIP_SRC})
  target_include_directories(kv_lwip PUBLIC ${HEV_LWIP}/src/include ${HEV_LWIP}/src/ports/include)
  target_compile_definitions(kv_lwip PRIVATE FD_SET_DEFINED SOCKLEN_T_DEFINED)

  file(GLOB_RECURSE HEV_YAML_SRC ${HEV_YAML}/src/*.c)
  add_library(kv_yaml STATIC ${HEV_YAML_SRC})
  target_include_directories(kv_yaml PRIVATE ${HEV_YAML}/src PUBLIC ${HEV_YAML}/include)
  target_compile_definitions(kv_yaml PRIVATE YAML_VERSION_MAJOR=0 YAML_VERSION_MINOR=2
    YAML_VERSION_PATCH=5 YAML_VERSION_STRING="0.2.5")

  file(GLOB_RECURSE HEV_SRC ${HEV}/src/*.c ${HEV}/src/*.S)
  list(FILTER HEV_SRC EXCLUDE REGEX ".*/hev-jni\\.c$") # we provide our own JNI
  add_library(kv_hev STATIC ${HEV_SRC})
  target_include_directories(kv_hev PRIVATE ${HEV}/src ${HEV}/src/misc ${HEV}/src/core/include
    PUBLIC ${HEV}/src)
  target_compile_definitions(kv_hev PRIVATE ENABLE_LIBRARY FD_SET_DEFINED SOCKLEN_T_DEFINED
    COMMIT_ID="fc3f900")
  target_link_libraries(kv_hev PUBLIC kv_yaml kv_lwip kv_hev_task_system)
  if(ANDROID)
    target_link_libraries(kv_hev PRIVATE log)
  endif()
  list(APPEND KV_LIBS kv_hev)
endif()

# ---- Kervan engine ----
add_library(kervan_core STATIC src/kervan_engine.c)
target_include_directories(kervan_core PUBLIC include PRIVATE src)
target_compile_options(kervan_core PRIVATE -Wall -Wextra -Werror=implicit-function-declaration)
if(KV_WITH_TUNNEL)
  target_compile_definitions(kervan_core PRIVATE KV_WITH_TUNNEL)
endif()
find_package(Threads REQUIRED)
target_link_libraries(kervan_core PUBLIC ${KV_LIBS} Threads::Threads)

if(KV_BUILD_TESTS)
  enable_testing()
  add_executable(kv_engine_test tests/test_engine.c)
  target_link_libraries(kv_engine_test PRIVATE kervan_core)
  add_test(NAME kv_engine_test COMMAND kv_engine_test)
  add_executable(kv_packet_mode_test tests/test_packet_mode.c)
  target_link_libraries(kv_packet_mode_test PRIVATE kervan_core)
  add_test(NAME kv_packet_mode_test COMMAND kv_packet_mode_test)
endif()
