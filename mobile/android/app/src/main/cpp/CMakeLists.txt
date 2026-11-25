cmake_minimum_required(VERSION 3.22)
project(kervan_android C ASM)

# Shared portable core (mobile/core). Run mobile/core/third_party/fetch.sh first.
set(KV_CORE_DIR ${CMAKE_CURRENT_SOURCE_DIR}/../../../../../core)
add_subdirectory(${KV_CORE_DIR} kervan_core)

add_library(kervan SHARED kervan_jni.c)
target_link_libraries(kervan PRIVATE kervan_core log)
target_compile_options(kervan PRIVATE -Wall -Wextra -Werror=implicit-function-declaration)
# 16 KB page-size compatibility (Android 15+ devices).
target_link_options(kervan PRIVATE -Wl,-z,max-page-size=16384 -Wl,-z,common-page-size=16384)
