#include <cinttypes>
#include <cstdint>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "presence.h"

namespace {
constexpr char TAG[] = "fyp";
constexpr TickType_t HEARTBEAT_INTERVAL = pdMS_TO_TICKS(2000);
// Synthetic test values only; radar timing and decision thresholds are not established.
constexpr fyp::Config TEST_CONFIG{1000, 2, 3};

void run_synthetic_self_test()
{
    fyp::PresenceMonitor test(TEST_CONFIG);
    bool ok = test.poll(0).presence == fyp::Presence::Unavailable;
    ok &= test.update({100, true, true}).presence == fyp::Presence::Unavailable;
    ok &= test.update({200, true, true}).presence == fyp::Presence::Occupied;
    ok &= test.update({300, true, false}).presence == fyp::Presence::Occupied;
    ok &= test.update({400, true, false}).presence == fyp::Presence::Occupied;
    ok &= test.update({500, true, false}).presence == fyp::Presence::Vacant;
    ok &= test.poll(1500).presence == fyp::Presence::Unavailable;
    ok &= test.update({1600, false, false}).presence == fyp::Presence::Unavailable;
    if (ok) {
        ESP_LOGI(TAG, "SYNTHETIC SELF-TEST PASS (not radar data)");
    } else {
        ESP_LOGE(TAG, "SYNTHETIC SELF-TEST FAIL (not radar data)");
    }
}
}

extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "FYP: radar input not implemented; live presence remains unavailable");
    run_synthetic_self_test();

    fyp::PresenceMonitor live(TEST_CONFIG);
    uint32_t heartbeat = 0;
    while (true) {
        const auto result = live.poll(0);
        ESP_LOGI(TAG, "LIVE heartbeat=%" PRIu32 " presence=%s radar=not_connected",
                 ++heartbeat, fyp::to_string(result.presence));
        vTaskDelay(HEARTBEAT_INTERVAL);
    }
}
