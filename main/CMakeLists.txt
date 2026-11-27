idf_component_register(SRCS "main.cpp" "../core/presence.cpp"
                       INCLUDE_DIRS "." "../core")

target_compile_features(${COMPONENT_LIB} PRIVATE cxx_std_17)
