cmake_minimum_required(VERSION 3.16)
project(fyp_host_tests LANGUAGES CXX)

enable_testing()
add_executable(presence_test presence_test.cpp ../core/presence.cpp)
target_include_directories(presence_test PRIVATE ../core)
target_compile_features(presence_test PRIVATE cxx_std_17)
add_test(NAME presence_test COMMAND presence_test)

add_executable(ti_mpd_packet_test ti_mpd_packet_test.cpp ../core/ti_mpd_packet.cpp ../core/radar_stream.cpp)
target_include_directories(ti_mpd_packet_test PRIVATE ../core)
target_compile_features(ti_mpd_packet_test PRIVATE cxx_std_17)
add_test(NAME ti_mpd_packet_test COMMAND ti_mpd_packet_test)
