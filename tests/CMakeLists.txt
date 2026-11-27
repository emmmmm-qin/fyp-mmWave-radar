cmake_minimum_required(VERSION 3.16)
project(fyp_host_tests LANGUAGES CXX)

enable_testing()
add_executable(presence_test presence_test.cpp ../core/presence.cpp)
target_include_directories(presence_test PRIVATE ../core)
target_compile_features(presence_test PRIVATE cxx_std_17)
add_test(NAME presence_test COMMAND presence_test)
