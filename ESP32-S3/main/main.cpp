#include <cstdio>
#include <cstdlib>
#include "sdkconfig.h"
#include "driver/uart.h"
#include "esp_timer.h"
#include "radar_stream.h"
#if !CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG
#error "Select USB Serial/JTAG as primary console for radar telemetry"
#endif
#include <cstdint>

#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "presence.h"

namespace {
constexpr char TAG[] = "fyp";
constexpr uart_port_t port = static_cast<uart_port_t>(CONFIG_FYP_RADAR_UART);
static_assert(CONFIG_FYP_RADAR_RX >= 4 && CONFIG_FYP_RADAR_RX <= 18);
struct Sample { fyp::radar::Frame frame; std::uint64_t time; bool valid; };
QueueHandle_t mailbox;
fyp::radar::Stream stream;
fyp::radar::Heartbeat heartbeat;
Sample latest{}; // RX task only; queue copies the value, never a borrowed pointer.
std::uint64_t uptime() { return static_cast<std::uint64_t>(esp_timer_get_time()) / 1000; }
void received(const fyp::radar::Frame& frame, std::uint64_t now) {
    latest.frame = frame;
    latest.time = now;
    latest.valid = true;
    heartbeat.valid(now);
    xQueueOverwrite(mailbox, &latest);
}
void output(void*) {
    static char line[fyp::radar::line_capacity];
    Sample sample;
    for (;;) {
        xQueueReceive(mailbox, &sample, portMAX_DELAY);
        const auto n = fyp::radar::encode(line, sizeof line, sample.valid ? &sample.frame : nullptr, sample.time);
        if (n) std::fwrite(line, 1, n, stdout);
    }
}
esp_err_t configure_uart() {
    uart_config_t config{};
    config.baud_rate = CONFIG_FYP_RADAR_BAUD;
    config.data_bits = UART_DATA_8_BITS;
    config.parity = UART_PARITY_DISABLE;
    config.stop_bits = UART_STOP_BITS_1;
    config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    config.source_clk = UART_SCLK_DEFAULT;
    auto err = uart_param_config(port, &config);
    if (err == ESP_OK) err = uart_set_pin(port, UART_PIN_NO_CHANGE, CONFIG_FYP_RADAR_RX,
                                         UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE);
    if (err == ESP_OK) err = uart_driver_install(port, 16384, 0, 0, nullptr, 0);
    return err;
}
void receive(void*) {
    const auto err = configure_uart();
    if (err != ESP_OK) ESP_LOGE(TAG, "Radar UART initialization failed: %s", esp_err_to_name(err));
    std::uint8_t bytes[512];
    for (;;) {
        const int n = err == ESP_OK ? uart_read_bytes(port, bytes, sizeof bytes, pdMS_TO_TICKS(20)) : 0;
        if (err != ESP_OK || n < 0) vTaskDelay(pdMS_TO_TICKS(50));
        const auto now = uptime();
        stream.feed(bytes, n > 0 ? static_cast<std::size_t>(n) : 0, now, received);
        if (heartbeat.due(now)) {
            latest.valid = false;
            latest.time = now;
            xQueueOverwrite(mailbox, &latest);
        }
    }
}
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
    run_synthetic_self_test();
    mailbox = xQueueCreate(1, sizeof(Sample));
    if (!mailbox || xTaskCreate(output, "radar-usb", 8192, nullptr, 3, nullptr) != pdPASS ||
        xTaskCreate(receive, "radar-rx", 16384, nullptr, 5, nullptr) != pdPASS) {
        ESP_LOGE(TAG, "Cannot allocate radar tasks or mailbox");
        std::abort();
    }
}
