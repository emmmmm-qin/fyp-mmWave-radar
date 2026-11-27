#include "ti_mpd_packet.h"

#include <algorithm>
#include <cmath>
#include <cstring>
#include <limits>

namespace fyp::ti_mpd {
namespace {
constexpr std::array<std::uint8_t, 8> SYNC_WORD{2, 1, 4, 3, 6, 5, 8, 7};
constexpr std::uint32_t SDK_VERSION = 0x05050402;
constexpr std::uint32_t XWRL6432_PLATFORM = 0x000A6432;
constexpr std::uint32_t COMPRESSED_CLOUD_TLV = 301;
constexpr std::size_t FRAME_HEADER_SIZE = 40;
constexpr std::size_t TLV_HEADER_SIZE = 8;
constexpr std::size_t PACKET_ALIGNMENT = 32;
constexpr std::size_t CLOUD_HEADER_SIZE = 20;
constexpr std::size_t POINT_SIZE = 10;

std::uint16_t read_u16(const std::uint8_t* data)
{
    return static_cast<std::uint16_t>(data[0] | (static_cast<std::uint16_t>(data[1]) << 8));
}

std::int32_t read_i16(const std::uint8_t* data)
{
    const std::int32_t raw = read_u16(data);
    return raw < 0x8000 ? raw : raw - 0x10000;
}

std::uint32_t read_u32(const std::uint8_t* data)
{
    return read_u16(data) | (static_cast<std::uint32_t>(read_u16(data + 2)) << 16);
}

float read_f32(const std::uint8_t* data)
{
    static_assert(sizeof(float) == 4 && std::numeric_limits<float>::is_iec559);
    const auto bits = read_u32(data);
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

bool valid_scale(float value)
{
    return std::isfinite(value) && value > 0.0f;
}

bool decode_cloud(const std::uint8_t* data, std::size_t size, Frame& frame)
{
    const std::size_t count = frame.reported_point_count;
    if (frame.has_cloud() || count == 0 || size != CLOUD_HEADER_SIZE + count * POINT_SIZE) {
        return false;
    }

    const float xyz = read_f32(data);
    const float doppler = read_f32(data + 4);
    const float snr = read_f32(data + 8);
    const float noise = read_f32(data + 12);
    const auto major = read_u16(data + 16);
    const auto minor = read_u16(data + 18);
    if (!valid_scale(xyz) || !valid_scale(doppler) || !valid_scale(snr) || !valid_scale(noise) ||
        static_cast<std::size_t>(major) + minor != count) {
        return false;
    }

    // The sender writes major-motion points first, followed by minor-motion points.
    const auto* point = data + CLOUD_HEADER_SIZE;
    for (std::size_t i = 0; i < count; ++i, point += POINT_SIZE) {
        const Point decoded{read_i16(point) * xyz, read_i16(point + 2) * xyz,
                            read_i16(point + 4) * xyz, read_i16(point + 6) * doppler,
                            point[8] * snr, point[9] * noise};
        if (!std::isfinite(decoded.x_m) || !std::isfinite(decoded.y_m) ||
            !std::isfinite(decoded.z_m) || !std::isfinite(decoded.radial_velocity_mps) ||
            !std::isfinite(decoded.snr_db) || !std::isfinite(decoded.noise_db)) {
            return false;
        }
        frame.points[i] = decoded;
    }
    frame.major_count = major;
    frame.minor_count = minor;
    return true;
}
} // namespace

DecodeResult decode_packet(const std::uint8_t* data, std::size_t size)
{
    if (data == nullptr || size < FRAME_HEADER_SIZE ||
        !std::equal(SYNC_WORD.begin(), SYNC_WORD.end(), data)) {
        return {DecodeStatus::InvalidHeader, {}};
    }
    if (read_u32(data + 8) != SDK_VERSION || read_u32(data + 16) != XWRL6432_PLATFORM) {
        return {DecodeStatus::UnsupportedFormat, {}};
    }
    if (read_u32(data + 12) != size || size % PACKET_ALIGNMENT != 0) {
        return {DecodeStatus::InvalidLength, {}};
    }

    Frame frame;
    frame.number = read_u32(data + 20);
    frame.reported_point_count = read_u32(data + 28);
    if (frame.reported_point_count > MAX_POINTS) {
        return {DecodeStatus::InvalidCloud, {}};
    }

    std::size_t offset = FRAME_HEADER_SIZE;
    const auto tlv_count = read_u32(data + 32);
    if (tlv_count == 0 || tlv_count > (size - offset) / TLV_HEADER_SIZE) {
        return {DecodeStatus::InvalidTlv, {}};
    }
    for (std::uint32_t i = 0; i < tlv_count; ++i) {
        if (size - offset < TLV_HEADER_SIZE) {
            return {DecodeStatus::InvalidTlv, {}};
        }
        const auto type = read_u32(data + offset);
        // TI's TLV length excludes the TLV header itself.
        const std::size_t length = read_u32(data + offset + 4);
        offset += TLV_HEADER_SIZE;
        if (length > size - offset) {
            return {DecodeStatus::InvalidTlv, {}};
        }
        if (type == COMPRESSED_CLOUD_TLV && !decode_cloud(data + offset, length, frame)) {
            return {DecodeStatus::InvalidCloud, {}};
        }
        offset += length;
    }

    // The sender specifies the amount of padding, not its contents.
    const auto padding = (PACKET_ALIGNMENT - offset % PACKET_ALIGNMENT) % PACKET_ALIGNMENT;
    if (size - offset != padding) {
        return {DecodeStatus::InvalidLength, {}};
    }
    return {DecodeStatus::Ok, frame};
}

} // namespace fyp::ti_mpd
