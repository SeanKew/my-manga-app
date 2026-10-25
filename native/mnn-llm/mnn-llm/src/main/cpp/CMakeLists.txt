cmake_minimum_required(VERSION 3.22.1)
project(mnn_llm_jni LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(MNN_JNI_LIBS "${CMAKE_CURRENT_SOURCE_DIR}/../jniLibs/arm64-v8a")
set(MNN_INCLUDE_DIR "${CMAKE_CURRENT_SOURCE_DIR}/include")

foreach(lib MNN MNN_Express llm)
    if(NOT EXISTS "${MNN_JNI_LIBS}/lib${lib}.so")
        message(FATAL_ERROR "Missing ${MNN_JNI_LIBS}/lib${lib}.so. Build MNN with LLM support and copy the arm64-v8a libraries.")
    endif()
    add_library(${lib} SHARED IMPORTED)
    set_target_properties(${lib} PROPERTIES IMPORTED_LOCATION "${MNN_JNI_LIBS}/lib${lib}.so")
endforeach()

add_library(mnn_llm_jni SHARED llm_jni.cpp)
target_include_directories(mnn_llm_jni PRIVATE "${MNN_INCLUDE_DIR}")
find_library(log-lib log)

target_link_libraries(mnn_llm_jni PRIVATE MNN MNN_Express llm ${log-lib})
