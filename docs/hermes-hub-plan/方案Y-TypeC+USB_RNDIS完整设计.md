# 🎯 Hermes HUB 架构 Y:TypeC + USB RNDIS 完整设计

> **JM 的选择**: 方案 Y (TypeC 多通道)  
> **核心**: 一根 TypeC 线 = 数据 + 网络 + 供电  
> **状态**: JM 正在找 TypeC 线,我同步出代码

---

## 📐 架构总览(权威)

```
┌─────────────────────────────────────────────────────────────┐
│  ESP32-S3 (CoreS3SE)         TypeC           OPPO A58        │
│  ┌──────────────┐          USB 母头          ┌─────────────┐ │
│  │ USB Host     │ ←─────── (3 通道) ───────→│ USB Device   │ │
│  │ Driver       │                            │              │ │
│  │              │ 1. CDC Serial 双向 JSON  │  Android USB  │ │
│  │  USB CDC ◄───────────────────────────►  │  Serial API   │ │
│  │  USB RNDIS ◄───────────────────────────►│  USB Tether   │ │
│  │  USB PD IN ◄────────────────────────────│  (供电 5V)   │ │
│  └──────┬───────┘                            └──────┬───────┘ │
│         │                                            │         │
│         │ (ESP32 WiFi 仍可用)                       │ WiFi   │
│         │                                            │        │
└─────────┼────────────────────────────────────────────┼────────┘
          │                                            │
          ▼                                            ▼
   voice_bridge (本机)                       WiFi AP / 4G 上网
   ws://183.48.74.9:443                            │
                                          (A58 共享网络)
```

---

## 🔌 USB 通道拆解

### 通道 1:**USB CDC 串口**(双向 JSON 通讯)

```
ESP32-S3 USB CDC ACM 端点:
  - Endpoint 0x01: OUT (ESP32 → A58)
  - Endpoint 0x81: IN  (A58 → ESP32)
  - Line Coding: 115200 bps, 8N1
  
A58 Android USB CDC 端:
  - UsbDeviceConnection
  - bulkTransfer(ep1, buf, len, timeout)
  - 监听 USB ACTION_ATTACHED 广播
  
数据格式(双方约定 JSON):
  ESP32 → A58:
    {"type":"device_state","online":true,"emotion":"happy","fw":"v3.1"}
    {"type":"action","name":"wave","timestamp":1726384000}
    {"type":"telemetry","battery":85,"temperature":42}
    
  A58 → ESP32:
    {"type":"cmd","action":"wave","req_id":"abc123"}
    {"type":"config","key":"wifi.ssid","value":"JM-A58"}
    {"type":"ota_update","url":"https://...","version":"v3.2"}
```

### 通道 2:**USB RNDIS 网络共享**(ESP32 通过 A58 上网)

```
A58 端: 设置 → 个人热点 → USB 共享网络
  ↓
A58 给 ESP32 分配 IP: 192.168.42.x (默认 RNDIS 子网)
  ↓
ESP32 端 usb_net 驱动:
  - Vendor ID: 0x18d1 (Google RNDIS)
  - dhcp client 自动获取 IP
  - 走标准 socket 连 WSS
```

### 通道 3:**USB PD 供电**

```
A58 TypeC 口输出: 5V/500mA (USB 2.0 默认)
CoreS3SE 功耗: 峰值 240mA @ 5V
= 足够
= 不需要额外电源
```

---

## 📋 完整实施计划(JM 找线时同步执行)

### Phase 0:**30 分钟基础验证**(等 JM 找好线)

#### 0.1 TypeC 物理连接(1 分钟)
```
JM 操作:
  1. A58 TypeC 母口 ←TypeC 公→ CoreS3SE TypeC 母口
  2. 或 A58 ←TypeC→ 转接头 ←TypeC→ CoreS3SE
  ⚠️ 确保线是"数据线"(不是纯充电线)
```

#### 0.2 A58 端:开启 USB Tethering
```bash
# 方法 1: JM 手动
设置 → 个人热点 → 更多共享设置 → USB 共享网络 → 开启

# 方法 2: 我远程 ADB(JM 设备开机后)
adb shell svc usb set_functions rndis

# 验证
adb shell ip addr show rndis0
# 期望看到 inet 192.168.42.x/24
```

#### 0.3 A58 端:识别 USB 设备
```bash
# 验证 RNDIS 设备
adb shell lsusb
# 期望看到: ID 0e8d:0004 MediaTek Inc.

# 验证 CDC 串口(可能需要 lsusb -v)
adb shell lsusb -v -d 0e8d:0004
# 期望看到:
#   bInterfaceClass 2 Communications
#   bInterfaceSubClass 2 Abstract (modem)
```

#### 0.4 ESP32 端:验证 USB Host
```cpp
// 烧录 usb_host_test.ino 后,串口看输出
// 期望看到:
// [USB Host] Device attached
// [USB CDC] Interface found
// [USB RNDIS] Interface found
// [DHCP] Got IP: 192.168.42.123
```

### Phase 1:**写固件 + App**(1-2 周)

#### 1.1 ESP32 USB Host 固件

```
项目结构:
  /home/ubuntu/phonebot-r1/dist/firmware/v3_2_usb_host/
    ├── phonebot_cores3se_v3_2_usb_host.ino
    ├── usb_host_driver.h
    ├── usb_cdc_handler.h
    ├── usb_rndis_handler.h
    └── config.h
```

#### 1.2 A58 App USB Serial 接收

```
项目结构:
  /home/ubuntu/phonebot-r1/app/src/main/java/com/phonebot/r1/usb/
    ├── UsbSerialManager.java
    ├── UsbSerialReceiver.java
    └── UsbRNDISManager.java
```

### Phase 2:**测试 + 调优**(3-5 天)

#### 2.1 端到端测试
```
1. TypeC 接好,JM 找线成功
2. A58 开 USB Tethering
3. ESP32 自动连 RNDIS,获 IP
4. ESP32 WSS 连本机 voice_bridge
5. A58 USB CDC 收 JSON,显示在 App
6. wave/nod 测试
7. logcat + device state 发飞书
```

#### 2.2 稳定性测试
```
- 连续运行 24 小时
- 4G/WiFi 切换测试
- A58 拔线重插恢复
- TypeC 线松脱检测
```

---

## 🛠️ 关键代码框架(JM 找线时我开始写)

### 1. ESP32-S3 USB Host 配置

```cpp
// phonebot_cores3se_v3_2_usb_host.ino
#include "usb/usb_host.h"
#include "usb/cdc_acm_host.h"
#include "usb/rndis_host.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "nvs_flash.h"

// USB Host 任务
static void usb_host_task(void *arg) {
    // 安装 USB Host 驱动
    usb_host_config_t host_config = {
        .skip_phy_setup = false,
        .intr_flags = ESP_INTR_FLAG_LEVEL1,
    };
    ESP_ERROR_CHECK(usb_host_install(&host_config));
    
    // 阻塞等待 USB 设备连接
    const usb_host_client_config_t client_config = {
        .is_synchronous = false,
        .max_num_event_msg = 5,
        .async = {
            .client_event_callback = usb_client_event_callback,
            .callback_arg = NULL,
        },
    };
    usb_host_client_handle_t client_handle;
    ESP_ERROR_CHECK(usb_host_client_register(&client_config, &client_handle));
    
    while (1) {
        // 处理 USB 事件
        usb_host_client_handle_events(client_handle, portMAX_DELAY);
        
        // 列举设备
        usb_device_handle_t dev_handle;
        if (usb_host_client_fetch_new_device(client_handle, &dev_handle) == ESP_OK) {
            ESP_LOGI("USB", "New device attached");
            
            // 解析设备描述符
            const usb_device_desc_t *dev_desc;
            if (usb_host_get_device_descriptor(dev_handle, &dev_desc) == ESP_OK) {
                ESP_LOGI("USB", "VID=0x%04x PID=0x%04x", 
                         dev_desc->idVendor, dev_desc->idProduct);
                
                // 打开 CDC 接口(假设 A58 是 CDC+RNDIS 复合设备)
                // ...
            }
        }
    }
}

void setup() {
    Serial.begin(115200);
    
    // 初始化 NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // 启动 USB Host 任务
    xTaskCreate(usb_host_task, "usb_host", 4096, NULL, 5, NULL);
}

void loop() {
    // 主循环:等待 USB CDC 数据
    if (cdc_dev_handle != NULL) {
        uint8_t buf[256];
        int actual_size = 0;
        if (cdc_acm_host_read(cdc_dev_handle, buf, sizeof(buf), &actual_size, 1000) == ESP_OK) {
            // 处理来自 A58 的 JSON 命令
            handle_command_from_a58(buf, actual_size);
        }
    }
    
    // 每 5 秒报告 ESP32 状态到 A58
    static uint32_t last_report = 0;
    if (millis() - last_report > 5000) {
        send_device_state_to_a58();
        last_report = millis();
    }
    
    delay(10);
}
```

### 2. ESP32 CDC 双向通讯

```cpp
// usb_cdc_handler.h
typedef struct {
    cdc_acm_host_dev_handle_t dev_handle;
    uint8_t bulk_in_ep;
    uint8_t bulk_out_ep;
    uint16_t bulk_in_packet_size;
} cdc_context_t;

static cdc_context_t s_cdc_ctx = {0};

// CDC 事件回调(收 A58 数据)
static void cdc_rx_callback(uint8_t *data, size_t data_len, void *user_arg) {
    if (data_len == 0) return;
    
    // 解析 JSON 命令
    char *json_str = strndup((char*)data, data_len);
    ESP_LOGI("CDC_RX", "Got %d bytes: %s", data_len, json_str);
    
    cJSON *root = cJSON_Parse(json_str);
    if (root) {
        cJSON *type = cJSON_GetObjectItem(root, "type");
        if (type && strcmp(type->valuestring, "cmd") == 0) {
            // 处理动作命令
            cJSON *action = cJSON_GetObjectItem(root, "action");
            if (action) {
                if (strcmp(action->valuestring, "wave") == 0) {
                    play_emotion("wave");
                } else if (strcmp(action->valuestring, "nod") == 0) {
                    play_emotion("nod");
                } else if (strcmp(action->valuestring, "happy") == 0) {
                    play_emotion("happy");
                }
                // ...
            }
        }
        cJSON_Delete(root);
    }
    free(json_str);
}

// ESP32 → A58
esp_err_t send_to_a58(const char *json_str) {
    if (s_cdc_ctx.dev_handle == NULL) return ESP_FAIL;
    return cdc_acm_host_write(s_cdc_ctx.dev_handle, 
                              (uint8_t*)json_str, strlen(json_str), 1000);
}

// 报告设备状态(每 5 秒)
void send_device_state_to_a58() {
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "type", "device_state");
    cJSON_AddBoolToObject(root, "online", true);
    cJSON_AddStringToObject(root, "emotion", current_emotion);
    cJSON_AddNumberToObject(root, "battery", read_battery());
    
    char *json_str = cJSON_PrintUnformatted(root);
    send_to_a58(json_str);
    
    free(json_str);
    cJSON_Delete(root);
}
```

### 3. ESP32 USB RNDIS 网络配置

```cpp
// usb_rndis_handler.h
#include "esp_netif.h"
#include "lwip/sockets.h"

static esp_netif_t *s_rndis_netif = NULL;

void rndis_event_handler(void *arg, esp_event_base_t event_base,
                        int32_t event_id, void *event_data) {
    if (event_base == NETIF_PPP_STATUS) {
        // RNDIS 类似 PPP,处理连接状态
    } else if (event_base == IP_EVENT) {
        ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
        ESP_LOGI("RNDIS", "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        
        // 连接本机 voice_bridge
        connect_voice_bridge();
    }
}

void init_rndis_netif() {
    // 配置 RNDIS 网络接口
    esp_netif_config_t netif_config = ESP_NETIF_DEFAULT_PPP();
    s_rndis_netif = esp_netif_new(&netif_config);
    
    // 注册事件
    esp_event_handler_register(IP_EVENT, IP_EVENT_PPP_GOT_IP, 
                               rndis_event_handler, NULL);
}

// 连接 voice_bridge(走 RNDIS 网络)
void connect_voice_bridge() {
    const char *host = "183.48.74.9";  // 本机公网 IP
    const int port = 443;
    const char *path = "/phonebot/ws/voice";
    
    // 用 WebSocket 客户端连
    extern void ws_client_connect(const char *host, int port, const char *path);
    ws_client_connect(host, port, path);
}
```

### 4. A58 端 USB Serial 接收

```java
// UsbSerialManager.java
package com.phonebot.r1.usb;

import android.app.PendingIntent;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.hardware.usb.UsbDevice;
import android.hardware.usb.UsbDeviceConnection;
import android.hardware.usb.UsbEndpoint;
import android.hardware.usb.UsbInterface;
import android.hardware.usb.UsbManager;
import android.os.Handler;
import android.os.HandlerThread;
import android.util.Log;
import com.phonebot.r1.bridge.VoiceBridge;
import org.json.JSONObject;

public class UsbSerialManager {
    private static final String TAG = "UsbSerial";
    private static final int VID_CORES3SE = 0x303a;  // ESP32-S3 USB 设备 VID
    
    private final UsbManager usbManager;
    private final Context context;
    private final HandlerThread ioThread;
    private final Handler ioHandler;
    private UsbDeviceConnection connection;
    private UsbEndpoint inEndpoint;
    private UsbEndpoint outEndpoint;
    private final VoiceBridge voiceBridge;
    
    public UsbSerialManager(Context context, VoiceBridge voiceBridge) {
        this.context = context;
        this.usbManager = (UsbManager) context.getSystemService(Context.USB_SERVICE);
        this.voiceBridge = voiceBridge;
        
        ioThread = new HandlerThread("UsbSerialIO");
        ioThread.start();
        ioHandler = new Handler(ioThread.getLooper());
        
        // 注册 USB 设备连接广播
        IntentFilter filter = new IntentFilter();
        filter.addAction("android.hardware.usb.action.USB_DEVICE_ATTACHED");
        filter.addAction("android.hardware.usb.action.USB_DEVICE_DETACHED");
        context.registerReceiver(usbReceiver, filter);
    }
    
    // USB 广播接收
    private final BroadcastReceiver usbReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context ctx, Intent intent) {
            String action = intent.getAction();
            UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
            
            if (UsbManager.ACTION_USB_DEVICE_ATTACHED.equals(action)) {
                if (device.getVendorId() == VID_CORES3SE) {
                    Log.i(TAG, "CoreS3SE attached: VID=" + device.getVendorId() 
                              + " PID=" + device.getProductId());
                    requestPermissionAndConnect(device);
                }
            } else if (UsbManager.ACTION_USB_DEVICE_DETACHED.equals(action)) {
                Log.i(TAG, "USB device detached");
                disconnect();
            }
        }
    };
    
    private void requestPermissionAndConnect(UsbDevice device) {
        PendingIntent permissionIntent = PendingIntent.getBroadcast(
            context, 0, new Intent("com.phonebot.r1.USB_PERMISSION"), 
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_MUTABLE
        );
        usbManager.requestPermission(device, permissionIntent);
    }
    
    public void onPermissionGranted(UsbDevice device) {
        ioHandler.post(() -> connect(device));
    }
    
    private void connect(UsbDevice device) {
        try {
            // 1. 打开设备
            connection = usbManager.openDevice(device);
            if (connection == null) {
                Log.e(TAG, "Failed to open USB device");
                return;
            }
            
            // 2. 找 CDC 接口(Interface Class 0x02 = Communications)
            UsbInterface cdcInterface = null;
            for (int i = 0; i < device.getInterfaceCount(); i++) {
                UsbInterface intf = device.getInterface(i);
                if (intf.getInterfaceClass() == 0x02) {
                    cdcInterface = intf;
                    break;
                }
            }
            
            if (cdcInterface == null) {
                Log.e(TAG, "No CDC interface found");
                return;
            }
            
            connection.claimInterface(cdcInterface, true);
            
            // 3. 找 Bulk 端点
            for (int i = 0; i < cdcInterface.getEndpointCount(); i++) {
                UsbEndpoint ep = cdcInterface.getEndpoint(i);
                if (ep.getType() == UsbConstants.USB_ENDPOINT_XFER_BULK) {
                    if (ep.getDirection() == UsbConstants.USB_DIR_IN) {
                        inEndpoint = ep;
                    } else if (ep.getDirection() == UsbConstants.USB_DIR_OUT) {
                        outEndpoint = ep;
                    }
                }
            }
            
            if (inEndpoint == null || outEndpoint == null) {
                Log.e(TAG, "Bulk endpoints not found");
                return;
            }
            
            Log.i(TAG, "Connected to CoreS3SE via USB CDC");
            
            // 4. 启动读循环
            ioHandler.post(this::readLoop);
            
            // 5. 启动 USB Tethering(让 ESP32 通过 A58 上网)
            enableUsbTethering();
            
        } catch (Exception e) {
            Log.e(TAG, "Connect failed", e);
        }
    }
    
    // 读 ESP32 数据
    private void readLoop() {
        byte[] buffer = new byte[256];
        while (connection != null) {
            try {
                int received = connection.bulkTransfer(inEndpoint, buffer, 
                                                        buffer.length, 1000);
                if (received > 0) {
                    String json = new String(buffer, 0, received);
                    Log.d(TAG, "RX: " + json);
                    handleEsp32Message(json);
                }
            } catch (Exception e) {
                Log.e(TAG, "Read error", e);
                break;
            }
        }
    }
    
    // 处理 ESP32 上报的 JSON
    private void handleEsp32Message(String json) {
        try {
            JSONObject obj = new JSONObject(json);
            String type = obj.optString("type");
            
            switch (type) {
                case "device_state":
                    boolean online = obj.optBoolean("online", false);
                    String emotion = obj.optString("emotion", "");
                    int battery = obj.optInt("battery", 0);
                    // 通知 VoiceBridge 更新
                    voiceBridge.onDeviceState(online, emotion, battery);
                    break;
                    
                case "action":
                    String name = obj.optString("name", "");
                    long timestamp = obj.optLong("timestamp", 0);
                    Log.i(TAG, "Action received: " + name);
                    break;
                    
                case "telemetry":
                    int temp = obj.optInt("temperature", 0);
                    Log.d(TAG, "Temperature: " + temp);
                    break;
            }
        } catch (Exception e) {
            Log.e(TAG, "Parse failed: " + json, e);
        }
    }
    
    // 发命令给 ESP32
    public void sendCommand(String action) {
        if (connection == null || outEndpoint == null) {
            Log.w(TAG, "Not connected, command dropped: " + action);
            return;
        }
        
        try {
            JSONObject obj = new JSONObject();
            obj.put("type", "cmd");
            obj.put("action", action);
            obj.put("req_id", java.util.UUID.randomUUID().toString());
            
            byte[] data = obj.toString().getBytes();
            int sent = connection.bulkTransfer(outEndpoint, data, data.length, 1000);
            Log.d(TAG, "TX: " + obj.toString() + " (" + sent + " bytes)");
        } catch (Exception e) {
            Log.e(TAG, "Send failed", e);
        }
    }
    
    // 开启 USB Tethering
    private void enableUsbTethering() {
        try {
            // 通过反射调用系统 API(ColorOS 兼容性需测试)
            // 实际可能需要 root 权限
            Log.i(TAG, "Attempting to enable USB tethering...");
            
            // 通过 ADB 命令(更可靠)
            // adb shell svc usb setfunctions rndis
            // 在外部执行
        } catch (Exception e) {
            Log.e(TAG, "Enable USB Tethering failed", e);
        }
    }
    
    public void disconnect() {
        if (connection != null) {
            connection.close();
            connection = null;
        }
    }
}
```

### 5. A58 端 USB 权限广播

```java
// UsbPermissionReceiver.java
public class UsbPermissionReceiver extends BroadcastReceiver {
    private static final String ACTION_USB_PERMISSION = 
        "com.phonebot.r1.USB_PERMISSION";
    private final UsbSerialManager manager;
    
    @Override
    public void onReceive(Context context, Intent intent) {
        if (ACTION_USB_PERMISSION.equals(intent.getAction())) {
            synchronized (this) {
                UsbDevice device = intent.getParcelableExtra(UsbManager.EXTRA_DEVICE);
                if (intent.getBooleanExtra(UsbManager.EXTRA_PERMISSION_GRANTED, false)) {
                    manager.onPermissionGranted(device);
                } else {
                    Log.e("UsbPerm", "Permission denied for device " + device);
                }
            }
        }
    }
}
```

### 6. 集成到 VoiceChatActivity

```java
// VoiceChatActivity.java 修改
public class VoiceChatActivity extends AppCompatActivity {
    private UsbSerialManager usbManager;
    
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        // 初始化 USB 串口管理
        usbManager = new UsbSerialManager(this, voiceBridge);
        
        // 注册权限广播
        UsbPermissionReceiver permReceiver = new UsbPermissionReceiver(usbManager);
        IntentFilter filter = new IntentFilter("com.phonebot.r1.USB_PERMISSION");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(permReceiver, filter, Context.RECEIVER_EXPORTED);
        } else {
            registerReceiver(permReceiver, filter);
        }
    }
    
    // 触发动作时,优先走 USB CDC
    private void triggerEmotion(String emotion) {
        // 1. 尝试 USB CDC(更可靠,延迟低)
        if (usbManager != null) {
            usbManager.sendCommand(emotion);
        }
        
        // 2. 备选:WSS(走 voice_bridge)
        voiceBridge.playEmotion(emotion);
    }
}
```

---

## 🆚 与方案 X 对比(为什么选 Y)

| 维度 | 方案 X (WiFi 热点) | 方案 Y (TypeC+USB) |
|---|---|---|
| **首次配置** | 需配 A58 热点 SSID/密码 | 即插即用,零配置 |
| **老人/儿童** | 不会配网 ❌ | 插线就行 ✅ |
| **网络不稳** | WiFi 抖动 ❌ | USB 稳定 ✅ |
| **离线降级** | 完全没网 ❌ | USB CDC 仍能用 ✅ |
| **烧固件** | 必须 TypeC 一次 | 必须 TypeC 一次 |
| **延迟** | WiFi 100-300ms | USB 1-5ms |
| **产品化** | 复杂 | 简单 |
| **成本** | TypeC 1 根 ¥20 | TypeC 1 根 ¥20 |

**结论**: Y 完胜 X,JM 选对了!

---

## 📋 JM 找线时我同步做的:

- [ ] ✅ 完整架构设计(本文)
- [ ] ⏳ ESP32 USB Host 固件(V3.2)
- [ ] ⏳ A58 USB Serial 接收(V3.3 App)
- [ ] ⏳ 端到端测试 SOP
- [ ] ⏳ 专利申请文档(3 项)

---

## 🎯 JM 找到线后:

1. 立即开始 Phase 0(30 分钟物理验证)
2. ADB 看 A58 是否识别 CoreS3SE RNDIS 设备
3. 测 USB CDC 双向通讯
4. 截图发飞书

---

*JM,我的代码已经在脑子里!等 JM 一根 TypeC 线!* ✨