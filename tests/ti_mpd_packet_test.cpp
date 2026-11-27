#include "ti_mpd_packet.h"

#include <cstdio>
#include <cstdlib>
#include <vector>

namespace {
using Bytes = std::vector<std::uint8_t>;
using fyp::ti_mpd::DecodeStatus;
using fyp::ti_mpd::decode_packet;

int failures = 0;

void check(bool condition, const char* label)
{
    if (!condition) {
        std::printf("FAIL: %s\n", label);
        ++failures;
    }
}

void put_u32(Bytes& bytes, std::size_t at, std::uint32_t value)
{
    for (std::size_t i = 0; i < 4; ++i) {
        bytes[at + i] = static_cast<std::uint8_t>(value >> (8 * i));
    }
}

Bytes header(std::uint32_t count, std::uint32_t tlvs)
{
    Bytes bytes{2, 1, 4, 3, 6, 5, 8, 7};
    bytes.resize(40);
    put_u32(bytes, 8, 0x05050402);
    put_u32(bytes, 16, 0xA6432);
    put_u32(bytes, 20, 42);
    put_u32(bytes, 28, count);
    put_u32(bytes, 32, tlvs);
    put_u32(bytes, 36, 0xFFFFFFFF);
    return bytes;
}

void append_tlv(Bytes& bytes, std::uint32_t type, const Bytes& payload)
{
    auto at = bytes.size();
    bytes.resize(at + 8);
    put_u32(bytes, at, type);
    put_u32(bytes, at + 4, static_cast<std::uint32_t>(payload.size()));
    bytes.insert(bytes.end(), payload.begin(), payload.end());
}

void finish(Bytes& bytes)
{
    // Use nonzero padding to catch accidental assumptions about its contents.
    bytes.resize((bytes.size() + 31) / 32 * 32, 0xA5);
    put_u32(bytes, 12, static_cast<std::uint32_t>(bytes.size()));
}

const Bytes CLOUD{
    // Synthetic scales: 0.25 m, 0.5 m/s, 0.25 dB and 2 dB.
    0, 0, 0x80, 0x3E, 0, 0, 0, 0x3F, 0, 0, 0x80, 0x3E, 0, 0, 0, 0x40,
    1, 0, 1, 0, // One major point and one minor point.
    0xFC, 0xFF, 8, 0, 2, 0, 0xFD, 0xFF, 200, 130,
    0, 0, 0, 0, 0, 0x80, 0xFF, 0x7F, 4, 5,
};

void expect_status(const Bytes& bytes, DecodeStatus status, const char* label)
{
    const auto result = decode_packet(bytes.data(), bytes.size());
    check(result.status == status, label);
    if (status != DecodeStatus::Ok) {
        check(!result.frame.has_cloud() && result.frame.number == 0 &&
              result.frame.reported_point_count == 0 && result.frame.points[0].x_m == 0.0f,
              "failure returns no partial frame");
    }
}
} // namespace

int main()
{
    auto packet = header(2, 3);
    append_tlv(packet, 306, {1, 2, 3});
    const auto cloud_at = packet.size();
    append_tlv(packet, 301, CLOUD);
    append_tlv(packet, 315, {1});
    finish(packet);
    const auto decoded = decode_packet(packet.data(), packet.size());
    const auto& frame = decoded.frame;
    check(decoded.status == DecodeStatus::Ok && frame.number == 42 &&
          frame.reported_point_count == 2 && frame.has_cloud() &&
          frame.major_count == 1 && frame.minor_count == 1, "mixed cloud and skipped TLVs");
    const auto& first = frame.points[0];
    check(first.x_m == -1.0f && first.y_m == 2.0f && first.z_m == 0.5f &&
          first.radial_velocity_mps == -1.5f && first.snr_db == 50.0f &&
          first.noise_db == 260.0f, "signed coordinates and unsigned signal fields");
    const auto& second = frame.points[1];
    check(second.z_m == -8192.0f && second.radial_velocity_mps == 16383.5f,
          "signed 16-bit limits");

    for (std::uint32_t count : {0, 2}) {
        auto absent = header(count, 1);
        append_tlv(absent, 306, Bytes(16)); // 40 + 8 + 16, no padding required.
        finish(absent);
        const auto result = decode_packet(absent.data(), absent.size());
        check(result.status == DecodeStatus::Ok && !result.frame.has_cloud() &&
              result.frame.reported_point_count == count, "cloud absent, not a vacancy decision");
    }

    check(decode_packet(nullptr, 0).status == DecodeStatus::InvalidHeader, "null input");
    expect_status(Bytes(39), DecodeStatus::InvalidHeader, "short header");
    auto broken = packet;
    broken[0] = 0;
    expect_status(broken, DecodeStatus::InvalidHeader, "bad sync word");
    broken = packet;
    broken[8] = 3;
    expect_status(broken, DecodeStatus::UnsupportedFormat, "wrong SDK version");
    broken = packet;
    broken[16] = 0;
    expect_status(broken, DecodeStatus::UnsupportedFormat, "wrong platform");
    broken = packet;
    broken.pop_back();
    expect_status(broken, DecodeStatus::InvalidLength, "truncated packet");
    put_u32(broken, 12, static_cast<std::uint32_t>(broken.size()));
    expect_status(broken, DecodeStatus::InvalidLength, "unaligned packet");
    broken = packet;
    broken.resize(broken.size() + 32, 0);
    put_u32(broken, 12, static_cast<std::uint32_t>(broken.size()));
    expect_status(broken, DecodeStatus::InvalidLength, "excess padding");
    broken = packet;
    put_u32(broken, 32, 0);
    expect_status(broken, DecodeStatus::InvalidTlv, "no TLVs");
    put_u32(broken, 32, 0xFFFFFFFF);
    expect_status(broken, DecodeStatus::InvalidTlv, "impossible TLV count");
    broken = packet;
    put_u32(broken, cloud_at + 4, 0xFFFFFFFF);
    expect_status(broken, DecodeStatus::InvalidTlv, "oversized TLV");
    put_u32(broken, cloud_at + 4, 19);
    expect_status(broken, DecodeStatus::InvalidCloud, "short cloud header");
    broken = packet;
    put_u32(broken, 28, 101);
    expect_status(broken, DecodeStatus::InvalidCloud, "point capacity exceeded");
    put_u32(broken, 28, 1);
    expect_status(broken, DecodeStatus::InvalidCloud, "point length mismatch");
    broken = packet;
    broken[cloud_at + 8 + 16] = 2;
    expect_status(broken, DecodeStatus::InvalidCloud, "point count mismatch");
    for (std::uint32_t scale : {0u, 0xBF800000u, 0x7FC00000u, 0x7F800000u, 0x7F7FFFFFu}) {
        broken = packet;
        put_u32(broken, cloud_at + 8, scale);
        expect_status(broken, DecodeStatus::InvalidCloud, "invalid or overflowing scale");
    }
    broken = header(2, 2);
    append_tlv(broken, 301, CLOUD);
    append_tlv(broken, 301, CLOUD);
    finish(broken);
    expect_status(broken, DecodeStatus::InvalidCloud, "duplicate cloud");
    broken = header(0, 1);
    append_tlv(broken, 301, Bytes(20));
    finish(broken);
    expect_status(broken, DecodeStatus::InvalidCloud, "present cloud with no points");

    if (failures != 0) {
        return EXIT_FAILURE;
    }
    std::puts("PASS: synthetic TI MPD packet checks");
    return EXIT_SUCCESS;
}
