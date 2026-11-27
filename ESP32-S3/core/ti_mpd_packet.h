#pragma once

#include <array>
#include <cstddef>
#include <cstdint>

namespace fyp::ti_mpd {

inline constexpr std::size_t MAX_POINTS = 100;

struct Point {
    float x_m;
    float y_m;
    float z_m;
    float radial_velocity_mps;
    float snr_db;
    float noise_db;
};

struct Frame {
    std::uint32_t number = 0;
    std::uint32_t reported_point_count = 0;
    std::uint16_t major_count = 0;
    std::uint16_t minor_count = 0;
    std::array<Point, MAX_POINTS> points{};

    // A frame can be valid without a compressed cloud.
    bool has_cloud() const { return major_count != 0 || minor_count != 0; }
};

enum class DecodeStatus {
    Ok,
    InvalidHeader,
    UnsupportedFormat,
    InvalidLength,
    InvalidTlv,
    InvalidCloud,
};

struct DecodeResult {
    DecodeStatus status;
    Frame frame;
};

// Expects one complete MPD 05.05.04.02 packet, starting at its sync word.
// On failure, frame is empty. Decoding does not make an occupancy decision.
DecodeResult decode_packet(const std::uint8_t* data, std::size_t size);

} // namespace fyp::ti_mpd
