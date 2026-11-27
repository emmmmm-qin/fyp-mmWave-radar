idf_component_register(SRCS "main.cpp" "../core/presence.cpp" "../core/ti_mpd_packet.cpp" "../core/radar_stream.cpp"
                       INCLUDE_DIRS "." "../core" PRIV_REQUIRES esp_driver_uart esp_timer)

target_compile_features(${COMPONENT_LIB} PRIVATE cxx_std_17)
