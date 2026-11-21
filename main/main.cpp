#include <cinttypes>
#include <cstdint>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace {
constexpr char TAG[] = "fyp";
constexpr TickType_t HEARTBEAT_INTERVAL = pdMS_TO_TICKS(2000);
}

extern "C" void app_main(void)
{
    ESP_LOGI(TAG, "FYP radar template started; radar input is not implemented");

    uint32_t heartbeat = 0;
    while (true) {
        ESP_LOGI(TAG, "heartbeat=%" PRIu32 " presence=UNAVAILABLE", ++heartbeat);
        vTaskDelay(HEARTBEAT_INTERVAL);
    }
}
