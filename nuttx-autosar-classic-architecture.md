# 基于 NuttX + AUTOSAR Classic BSW 的自研整车操作系统架构方案

> **版本**: v1.0  
> **AUTOSAR 基线版本**: R22-11 Classic Platform  
> **目标架构**: 中央计算单元 (Central Computing Unit, CCU) + 区域控制器 (Zone Controller, ZC)  
> **底层 RTOS**: Apache NuttX

---

## 目录

1. [术语表](#1-术语表)
2. [架构总览与 draw.io 分层图](#2-架构总览与-drawio-分层图)
3. [NuttX 与 AUTOSAR OS 的适配设计](#3-nuttx-与-autosar-os-的适配设计)
4. [BSW 关键模块集成策略](#4-bsw-关键模块集成策略)
5. [功能安全与信息安全的具体落地方案](#5-功能安全与信息安全的具体落地方案)
6. [开发与集成建议](#6-开发与集成建议)

---

## 1. 术语表

| 缩写 | 全称 | 说明 |
|------|------|------|
| **MCAL** | Microcontroller Abstraction Layer | 微控制器抽象层，直接操作硬件寄存器的最底层驱动 |
| **ECU** | Electronic Control Unit | 电子控制单元 |
| **BSW** | Basic Software | 基础软件，AUTOSAR 中间件层的统称 |
| **RTE** | Runtime Environment | 运行时环境，连接 BSW 与 SWC 的中间层 |
| **SWC** | Software Component | 应用层软件组件 |
| **PDU** | Protocol Data Unit | 协议数据单元 |
| **I-PDU** | Interaction Layer PDU | 交互层协议数据单元 |
| **COM** | AUTOSAR Communication | AUTOSAR 通信服务模块 |
| **PduR** | PDU Router | PDU 路由模块 |
| **Dcm** | Diagnostic Communication Manager | 诊断通信管理器 |
| **Dem** | Diagnostic Event Manager | 诊断事件管理器 |
| **DoIP** | Diagnostics over IP | 基于 IP 的诊断协议 (ISO 13400) |
| **NvM** | NVRAM Manager | 非易失性存储管理器 |
| **MemIf** | Memory Abstraction Interface | 存储抽象接口 |
| **Fee** | Flash EEPROM Emulation | Flash EEPROM 仿真模块 |
| **EA** | EEPROM Abstraction | EEPROM 抽象模块 |
| **EcuM** | ECU State Manager | ECU 状态管理器 |
| **BswM** | BSW Mode Manager | BSW 模式管理器 |
| **CommM** | Communication Manager | 通信管理器 |
| **WdgM** | Watchdog Manager | 看门狗管理器 |
| **NM** | Network Management | 网络管理 |
| **SecOC** | Secure Onboard Communication | 安全车载通信 |
| **Csm** | Crypto Service Manager | 加密服务管理器 |
| **CryIf** | Crypto Interface | 加密接口 |
| **HSM** | Hardware Security Module | 硬件安全模块 |
| **MPU** | Memory Protection Unit | 内存保护单元 |
| **E2E** | End-to-End | 端到端（通信保护） |
| **SOME/IP** | Scalable service-Oriented MiddlewarE over IP | 面向服务的可扩展 IP 中间件 |
| **DDS** | Data Distribution Service | 数据分发服务 (OMG 标准) |
| **SMP** | Symmetric Multi-Processing | 对称多处理 |
| **AMP** | Asymmetric Multi-Processing | 非对称多处理 |
| **SIL** | Software-in-the-Loop | 软件在环测试 |
| **HIL** | Hardware-in-the-Loop | 硬件在环测试 |
| **CCU** | Central Computing Unit | 中央计算单元 |
| **ZC** | Zone Controller | 区域控制器 |

---

## 2. 架构总览与 draw.io 分层图

### 2.1 架构设计原则

1. **层级解耦**：严格遵循 AUTOSAR 分层架构，每层通过标准化接口交互，降低耦合度。
2. **NuttX 作为 OS 底座**：NuttX 内核位于 MCAL 之上，为所有 BSW 模块提供任务调度、中断管理、内存保护、网络协议栈等 OS 服务。
3. **跨域融合**：通过 CCU + ZC 架构实现动力、底盘、车身、座舱、ADAS 等多域融合。
4. **安全贯穿**：功能安全 (ISO 26262) 和信息安全 (ISO 21434) 机制贯穿所有层次。
5. **DDS 共存**：DDS 作为独立通信中间件，与 SOME/IP 在 BSW 通信服务层共存，通过桥接模块实现协议互通。

### 2.2 分层图颜色约定

| 颜色 | 含义 |
|------|------|
| 🔴 **红色/深红背景** (`#FFE0E0`) | 功能安全相关模块 |
| 🔵 **蓝色/深蓝背景** (`#E0E0FF`) | 信息安全相关模块 |
| 🟢 **绿色/深绿背景** (`#E0FFE0`) | DDS 相关模块 |
| ⬜ **灰色背景** (`#F5F5F5`) | 标准 BSW 模块 |
| 🟡 **黄色背景** (`#FFF2CC`) | NuttX 内核相关 |
| 🟠 **橙色背景** (`#FFE6CC`) | 硬件层 |

### 2.3 draw.io 架构分层图（mxGraph XML）

> 将以下 XML 内容完整复制，在 draw.io 中选择 **File → Import from → XML** 即可导入。

```xml
<mxfile host="app.diagrams.net" modified="2026-06-08T00:00:00.000Z" agent="Architecture Design" version="24.0.0" type="device">
  <diagram id="nuttx-autosar-arch" name="NuttX+AUTOSAR Classic Architecture">
    <mxGraphModel dx="2800" dy="3600" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="2400" pageHeight="3400" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

        <!-- ============================================================ -->
        <!-- LAYER 7: APPLICATION LAYER (SWC)                             -->
        <!-- ============================================================ -->
        <mxCell id="L7_title" value="&lt;b&gt;应用层 (Application Layer) — SWC&lt;/b&gt;" style="text;html=1;align=center;verticalAlign=middle;fontSize=16;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="40" y="10" width="2320" height="30" as="geometry"/>
        </mxCell>

        <!-- Application SWC Row -->
        <mxCell id="swc_powertrain" value="&lt;b&gt;动力域 SWC&lt;/b&gt;&lt;br&gt;Engine/Motor Control&lt;br&gt;Transmission" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="40" y="50" width="280" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="swc_chassis" value="&lt;b&gt;底盘域 SWC&lt;/b&gt;&lt;br&gt;ESP / EPS / iBooster&lt;br&gt;Air Suspension" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="340" y="50" width="280" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="swc_body" value="&lt;b&gt;车身域 SWC&lt;/b&gt;&lt;br&gt;Body Control&lt;br&gt;Lighting / Door / HVAC" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="640" y="50" width="280" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="swc_adas" value="&lt;b&gt;ADAS 域 SWC&lt;/b&gt;&lt;br&gt;Perception / Planning&lt;br&gt;Fusion / Control" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="940" y="50" width="280" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="swc_diag" value="&lt;b&gt;诊断应用 SWC&lt;/b&gt;&lt;br&gt;OBD / UDS Session&lt;br&gt;DTC Management" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1240" y="50" width="280" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="swc_ota" value="&lt;b&gt;OTA / 车云 SWC&lt;/b&gt;&lt;br&gt;FOTA Manager&lt;br&gt;Vehicle-Cloud Proxy" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1540" y="50" width="280" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="swc_safety_app" value="&lt;b&gt;[安全] 安全监控 SWC&lt;/b&gt;&lt;br&gt;Safety Monitor&lt;br&gt;Degradation Manager" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="1840" y="50" width="280" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="swc_dds_app" value="&lt;b&gt;[DDS] DDS 应用 SWC&lt;/b&gt;&lt;br&gt;Topic Publisher/Subscriber&lt;br&gt;Sensor Fusion via DDS" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=11;fontColor=#006600;" vertex="1" parent="1">
          <mxGeometry x="2140" y="50" width="220" height="70" as="geometry"/>
        </mxCell>

        <!-- ============================================================ -->
        <!-- LAYER 6: RTE (Runtime Environment)                           -->
        <!-- ============================================================ -->
        <mxCell id="L6_title" value="&lt;b&gt;运行时环境 (RTE — Runtime Environment)&lt;/b&gt;" style="text;html=1;align=center;verticalAlign=middle;fontSize=16;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="40" y="140" width="2320" height="30" as="geometry"/>
        </mxCell>

        <mxCell id="rte_main" value="&lt;b&gt;RTE (Auto-Generated)&lt;/b&gt;&lt;br&gt;Sender-Receiver / Client-Server Port 映射&lt;br&gt;Runnable → OS Task 映射 &amp; 调度触发" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#DAEEF3;strokeColor=#0078D4;fontSize=12;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="40" y="175" width="680" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="rte_e2e" value="&lt;b&gt;[功能安全] E2E Protection&lt;/b&gt;&lt;br&gt;E2E Transformer&lt;br&gt;注入点: RTE ↔ COM" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="740" y="175" width="320" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="rte_secoc_inject" value="&lt;b&gt;[信息安全] SecOC 注入点&lt;/b&gt;&lt;br&gt;Freshness Value Injection&lt;br&gt;MAC 校验触发" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1080" y="175" width="320" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="rte_dds_bridge" value="&lt;b&gt;[DDS] DDS-RTE Bridge&lt;/b&gt;&lt;br&gt;Topic ↔ S/R Port 映射&lt;br&gt;QoS → Runnable Trigger" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=11;fontColor=#006600;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1420" y="175" width="320" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="rte_mem_partition" value="&lt;b&gt;[功能安全] 内存分区隔离&lt;/b&gt;&lt;br&gt;OS-Application Partition&lt;br&gt;MPU Region 配置" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1760" y="175" width="320" height="55" as="geometry"/>
        </mxCell>

        <!-- ============================================================ -->
        <!-- LAYER 5: BSW SERVICE LAYER                                   -->
        <!-- ============================================================ -->
        <mxCell id="L5_title" value="&lt;b&gt;BSW 服务层 (Services Layer)&lt;/b&gt;" style="text;html=1;align=center;verticalAlign=middle;fontSize=16;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="40" y="250" width="2320" height="30" as="geometry"/>
        </mxCell>

        <!-- Communication Services -->
        <mxCell id="bsw_com_group" value="&lt;b&gt;通信服务 (Communication Services)&lt;/b&gt;" style="text;html=1;align=left;fontSize=12;fontStyle=1;fontColor=#555555;" vertex="1" parent="1">
          <mxGeometry x="40" y="285" width="400" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_com" value="&lt;b&gt;COM&lt;/b&gt;&lt;br&gt;Signal Gateway&lt;br&gt;I-PDU Group" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="40" y="310" width="160" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_pdur" value="&lt;b&gt;PduR&lt;/b&gt;&lt;br&gt;PDU Router&lt;br&gt;多路由/扇出" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="210" y="310" width="160" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_ipdum" value="&lt;b&gt;IpduM&lt;/b&gt;&lt;br&gt;I-PDU Multiplexer" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="380" y="310" width="140" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_someip" value="&lt;b&gt;SOME/IP&lt;/b&gt;&lt;br&gt;SD (Service Discovery)&lt;br&gt;Transformer" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#0078D4;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="530" y="310" width="170" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_secoc" value="&lt;b&gt;[信息安全] SecOC&lt;/b&gt;&lt;br&gt;Secure Onboard Comm&lt;br&gt;MAC + Freshness Mgmt" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="710" y="310" width="200" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_e2e_lib" value="&lt;b&gt;[功能安全] E2E Library&lt;/b&gt;&lt;br&gt;Profile 1/2/4/5/6/7&lt;br&gt;CRC + Counter" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="920" y="310" width="190" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_nm" value="&lt;b&gt;NM (Network Mgmt)&lt;/b&gt;&lt;br&gt;CanNm / UdpNm&lt;br&gt;Partial Networking" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1120" y="310" width="180" height="60" as="geometry"/>
        </mxCell>

        <!-- DDS Middleware Block -->
        <mxCell id="bsw_dds" value="&lt;b&gt;[DDS] DDS 通信中间件&lt;/b&gt;&lt;br&gt;Cyclone DDS Lite / Fast DDS&lt;br&gt;RTPS Protocol | Topic Discovery&lt;br&gt;DDS-SOME/IP Bridge" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=11;fontColor=#006600;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1310" y="310" width="260" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_dds_sec" value="&lt;b&gt;[DDS+信息安全]&lt;/b&gt;&lt;br&gt;&lt;b&gt;DDS-Security Plugin&lt;/b&gt;&lt;br&gt;Auth / Access Control&lt;br&gt;Crypto (AES-GCM)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#D0D0FF;strokeColor=#4400AA;fontSize=10;fontColor=#4400AA;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1580" y="310" width="200" height="60" as="geometry"/>
        </mxCell>

        <!-- Diagnostic Services -->
        <mxCell id="bsw_diag_group" value="&lt;b&gt;诊断服务 (Diagnostic Services)&lt;/b&gt;" style="text;html=1;align=left;fontSize=12;fontStyle=1;fontColor=#555555;" vertex="1" parent="1">
          <mxGeometry x="40" y="385" width="400" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_dcm" value="&lt;b&gt;Dcm&lt;/b&gt;&lt;br&gt;UDS (ISO 14229)&lt;br&gt;Session / Service Dispatch" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="40" y="410" width="200" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_dem" value="&lt;b&gt;Dem&lt;/b&gt;&lt;br&gt;DTC Storage&lt;br&gt;Event Debounce" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="250" y="410" width="180" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_fim" value="&lt;b&gt;FiM&lt;/b&gt;&lt;br&gt;Function Inhibition&lt;br&gt;Manager" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="440" y="410" width="160" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_doip" value="&lt;b&gt;DoIP&lt;/b&gt;&lt;br&gt;ISO 13400&lt;br&gt;TCP/TLS Transport" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="610" y="410" width="160" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_diag_sec" value="&lt;b&gt;[信息安全] 诊断安全访问&lt;/b&gt;&lt;br&gt;0x27 SecurityAccess&lt;br&gt;0x29 Authentication" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="780" y="410" width="220" height="55" as="geometry"/>
        </mxCell>

        <!-- Memory Services -->
        <mxCell id="bsw_mem_group" value="&lt;b&gt;存储服务 (Memory Services)&lt;/b&gt;" style="text;html=1;align=left;fontSize=12;fontStyle=1;fontColor=#555555;" vertex="1" parent="1">
          <mxGeometry x="1050" y="385" width="400" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_nvm" value="&lt;b&gt;NvM&lt;/b&gt;&lt;br&gt;Block Descriptor&lt;br&gt;Redundant / Resistant" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1050" y="410" width="180" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_memif" value="&lt;b&gt;MemIf&lt;/b&gt;&lt;br&gt;Memory Abstraction&lt;br&gt;Interface" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1240" y="410" width="160" height="55" as="geometry"/>
        </mxCell>

        <!-- System Services -->
        <mxCell id="bsw_sys_group" value="&lt;b&gt;系统服务 (System Services)&lt;/b&gt;" style="text;html=1;align=left;fontSize=12;fontStyle=1;fontColor=#555555;" vertex="1" parent="1">
          <mxGeometry x="1450" y="385" width="400" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_ecum" value="&lt;b&gt;EcuM&lt;/b&gt;&lt;br&gt;Startup/Shutdown&lt;br&gt;Sleep/Wakeup" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1450" y="410" width="150" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_bswm" value="&lt;b&gt;BswM&lt;/b&gt;&lt;br&gt;Mode Arbitration&lt;br&gt;Rule Engine" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1610" y="410" width="150" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_comm" value="&lt;b&gt;ComM&lt;/b&gt;&lt;br&gt;Comm Channel&lt;br&gt;State Machine" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1770" y="410" width="150" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_wdgm" value="&lt;b&gt;[功能安全] WdgM&lt;/b&gt;&lt;br&gt;Alive / Deadline / Logic&lt;br&gt;Supervision" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1930" y="410" width="190" height="55" as="geometry"/>
        </mxCell>

        <!-- Crypto Services -->
        <mxCell id="bsw_crypto_group" value="&lt;b&gt;加密服务 (Crypto Services)&lt;/b&gt;" style="text;html=1;align=left;fontSize=12;fontStyle=1;fontColor=#555555;" vertex="1" parent="1">
          <mxGeometry x="40" y="480" width="400" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_csm" value="&lt;b&gt;[信息安全] Csm&lt;/b&gt;&lt;br&gt;Crypto Service Manager&lt;br&gt;Job Queue / Callback" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="40" y="505" width="200" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_cryif" value="&lt;b&gt;[信息安全] CryIf&lt;/b&gt;&lt;br&gt;Crypto Interface&lt;br&gt;Driver Abstraction" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="250" y="505" width="200" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_keym" value="&lt;b&gt;[信息安全] KeyM&lt;/b&gt;&lt;br&gt;Key Manager&lt;br&gt;Certificate Mgmt" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="460" y="505" width="200" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_ids" value="&lt;b&gt;[信息安全] IdsM&lt;/b&gt;&lt;br&gt;Intrusion Detection&lt;br&gt;Security Event Mgmt" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="670" y="505" width="200" height="55" as="geometry"/>
        </mxCell>

        <!-- Network Firewall -->
        <mxCell id="bsw_firewall" value="&lt;b&gt;[信息安全] 网络防火墙&lt;/b&gt;&lt;br&gt;Ethernet Firewall&lt;br&gt;VLAN / ACL / Rate Limit" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="880" y="505" width="210" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_seclog" value="&lt;b&gt;[信息安全] 安全日志&lt;/b&gt;&lt;br&gt;Security Audit Log&lt;br&gt;Tamper Detection" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="1100" y="505" width="200" height="55" as="geometry"/>
        </mxCell>

        <!-- Safety Shutdown -->
        <mxCell id="bsw_safe_shutdown" value="&lt;b&gt;[功能安全] 安全关断路径&lt;/b&gt;&lt;br&gt;Safe State Manager&lt;br&gt;Degradation Control" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1350" y="505" width="220" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="bsw_flow_monitor" value="&lt;b&gt;[功能安全] 程序流监控&lt;/b&gt;&lt;br&gt;Checkpoint Sequence&lt;br&gt;WdgM Alive Supervision" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1580" y="505" width="230" height="55" as="geometry"/>
        </mxCell>

        <!-- OS Service (AUTOSAR OS API over NuttX) -->
        <mxCell id="bsw_os_api" value="&lt;b&gt;AUTOSAR OS API Shim&lt;/b&gt;&lt;br&gt;ActivateTask / GetResource / SetEvent&lt;br&gt;GetAlarm / StartScheduleTableRel" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1850" y="505" width="280" height="55" as="geometry"/>
        </mxCell>

        <!-- ============================================================ -->
        <!-- LAYER 4: ECU ABSTRACTION LAYER                               -->
        <!-- ============================================================ -->
        <mxCell id="L4_title" value="&lt;b&gt;ECU 抽象层 (ECU Abstraction Layer) &amp; 复杂驱动 (CDD)&lt;/b&gt;" style="text;html=1;align=center;verticalAlign=middle;fontSize=16;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="40" y="580" width="2320" height="30" as="geometry"/>
        </mxCell>

        <mxCell id="ecu_canif" value="&lt;b&gt;CanIf&lt;/b&gt;&lt;br&gt;CAN Interface" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="40" y="620" width="140" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_linif" value="&lt;b&gt;LinIf&lt;/b&gt;&lt;br&gt;LIN Interface" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="190" y="620" width="140" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_ethif" value="&lt;b&gt;EthIf&lt;/b&gt;&lt;br&gt;Ethernet Interface" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="340" y="620" width="140" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_soad" value="&lt;b&gt;SoAd&lt;/b&gt;&lt;br&gt;Socket Adaptor" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="490" y="620" width="140" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_tcpip" value="&lt;b&gt;TcpIp Stack&lt;/b&gt;&lt;br&gt;(NuttX Net Subsystem)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="640" y="620" width="170" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_fee" value="&lt;b&gt;Fee / EA&lt;/b&gt;&lt;br&gt;Flash/EEPROM Emu" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="820" y="620" width="150" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_wdgif" value="&lt;b&gt;WdgIf&lt;/b&gt;&lt;br&gt;Watchdog Interface" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="980" y="620" width="150" height="50" as="geometry"/>
        </mxCell>

        <!-- Complex Drivers -->
        <mxCell id="cdd_hsm" value="&lt;b&gt;[信息安全] CDD: HSM Driver&lt;/b&gt;&lt;br&gt;Crypto HW Acceleration&lt;br&gt;Secure Key Storage" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1150" y="620" width="220" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_sensor" value="&lt;b&gt;CDD: Sensor Fusion&lt;/b&gt;&lt;br&gt;Camera / Radar / Lidar&lt;br&gt;DMA + NuttX devfs" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1380" y="620" width="200" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_dds_transport" value="&lt;b&gt;[DDS] CDD: DDS Transport&lt;/b&gt;&lt;br&gt;RTPS over UDP/SHM&lt;br&gt;NuttX Socket Layer" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=11;fontColor=#006600;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1590" y="620" width="220" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_safe_path" value="&lt;b&gt;[功能安全] CDD: Safety Path&lt;/b&gt;&lt;br&gt;HW Diag / Reset Ctrl&lt;br&gt;Safe State Output" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1820" y="620" width="220" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_crypto_drv" value="&lt;b&gt;[信息安全] Crypto Driver&lt;/b&gt;&lt;br&gt;AES / SHA / RSA&lt;br&gt;HSM Mailbox" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="2050" y="620" width="180" height="50" as="geometry"/>
        </mxCell>

        <!-- ============================================================ -->
        <!-- LAYER 3: NuttX KERNEL (OS Layer)                             -->
        <!-- ============================================================ -->
        <mxCell id="L3_title" value="&lt;b&gt;NuttX 实时内核 (OS 底座 — 位于 MCAL 之上)&lt;/b&gt;" style="text;html=1;align=center;verticalAlign=middle;fontSize=16;fontColor=#8B6914;" vertex="1" parent="1">
          <mxGeometry x="40" y="690" width="2320" height="30" as="geometry"/>
        </mxCell>

        <mxCell id="nuttx_bg" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;strokeWidth=3;opacity=30;" vertex="1" parent="1">
          <mxGeometry x="30" y="725" width="2340" height="110" as="geometry"/>
        </mxCell>

        <mxCell id="nuttx_sched" value="&lt;b&gt;任务调度器&lt;/b&gt;&lt;br&gt;POSIX Threads&lt;br&gt;Priority Preemptive&lt;br&gt;FIFO / RR / Sporadic" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="40" y="730" width="200" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_ipc" value="&lt;b&gt;IPC 机制&lt;/b&gt;&lt;br&gt;Semaphore / Mutex&lt;br&gt;MQ / Signal&lt;br&gt;Shared Memory" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="250" y="730" width="200" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_mpu" value="&lt;b&gt;[功能安全] MPU/MMU 管理&lt;/b&gt;&lt;br&gt;内存分区&lt;br&gt;Protected / Kernel Build&lt;br&gt;Region Config" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFD0D0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="460" y="730" width="220" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_timer" value="&lt;b&gt;定时器 &amp; Tick&lt;/b&gt;&lt;br&gt;POSIX Timer&lt;br&gt;Watchdog Timer&lt;br&gt;Tickless Mode" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="690" y="730" width="190" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_irq" value="&lt;b&gt;中断管理&lt;/b&gt;&lt;br&gt;IRQ Dispatch&lt;br&gt;Nested Interrupt&lt;br&gt;ISR Cat1/Cat2 映射" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="890" y="730" width="190" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_net" value="&lt;b&gt;网络子系统&lt;/b&gt;&lt;br&gt;BSD Socket API&lt;br&gt;TCP/UDP/IP&lt;br&gt;Ethernet Driver" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1090" y="730" width="190" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_fs" value="&lt;b&gt;文件系统&lt;/b&gt;&lt;br&gt;VFS / devfs&lt;br&gt;LittleFS / FAT&lt;br&gt;MTD Driver" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1290" y="730" width="180" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_smp" value="&lt;b&gt;多核支持&lt;/b&gt;&lt;br&gt;SMP Scheduler&lt;br&gt;CPU Affinity&lt;br&gt;Inter-Core IPC" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1480" y="730" width="190" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_openamp" value="&lt;b&gt;OpenAMP / RPMsg&lt;/b&gt;&lt;br&gt;AMP 核间通信&lt;br&gt;Remoteproc&lt;br&gt;Virtio Transport" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1680" y="730" width="200" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_secboot" value="&lt;b&gt;[信息安全] Secure Boot&lt;/b&gt;&lt;br&gt;Bootloader Chain&lt;br&gt;Image Verify (HSM)&lt;br&gt;Anti-Rollback" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#D0D0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1890" y="730" width="210" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_time_prot" value="&lt;b&gt;[功能安全] 时间保护&lt;/b&gt;&lt;br&gt;Execution Budget&lt;br&gt;OS Timer + WdgM" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFD0D0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="2110" y="730" width="190" height="70" as="geometry"/>
        </mxCell>

        <!-- ============================================================ -->
        <!-- LAYER 2: MCAL (Microcontroller Abstraction Layer)            -->
        <!-- ============================================================ -->
        <mxCell id="L2_title" value="&lt;b&gt;MCAL — 微控制器抽象层 (Microcontroller Abstraction Layer)&lt;/b&gt;" style="text;html=1;align=center;verticalAlign=middle;fontSize=16;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="40" y="850" width="2320" height="30" as="geometry"/>
        </mxCell>

        <mxCell id="mcal_can" value="&lt;b&gt;Can Driver&lt;/b&gt;&lt;br&gt;CAN / CAN FD" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="40" y="890" width="150" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_lin" value="&lt;b&gt;Lin Driver&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="200" y="890" width="120" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_eth" value="&lt;b&gt;Eth Driver&lt;/b&gt;&lt;br&gt;MAC + PHY" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="330" y="890" width="150" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_spi" value="&lt;b&gt;Spi Driver&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="490" y="890" width="120" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_dio" value="&lt;b&gt;Dio Driver&lt;/b&gt;&lt;br&gt;GPIO" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="620" y="890" width="120" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_adc" value="&lt;b&gt;Adc Driver&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="750" y="890" width="110" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_pwm" value="&lt;b&gt;Pwm Driver&lt;/b&gt;" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="870" y="890" width="110" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_gpt" value="&lt;b&gt;Gpt Driver&lt;/b&gt;&lt;br&gt;Timer" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="990" y="890" width="120" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_icu" value="&lt;b&gt;Icu Driver&lt;/b&gt;&lt;br&gt;Input Capture" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1120" y="890" width="130" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_fls" value="&lt;b&gt;Fls Driver&lt;/b&gt;&lt;br&gt;Flash" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1260" y="890" width="130" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_wdg" value="&lt;b&gt;[功能安全] Wdg Driver&lt;/b&gt;&lt;br&gt;Internal/External WDT" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="1400" y="890" width="190" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_mcu" value="&lt;b&gt;Mcu Driver&lt;/b&gt;&lt;br&gt;Clock / Reset / PLL" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1600" y="890" width="160" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_port" value="&lt;b&gt;Port Driver&lt;/b&gt;&lt;br&gt;Pin Mux" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1770" y="890" width="130" height="50" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_hwdiag" value="&lt;b&gt;[功能安全] HW Diag&lt;/b&gt;&lt;br&gt;ECC / Lockstep&lt;br&gt;BIST / Voltage Mon" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1910" y="890" width="200" height="50" as="geometry"/>
        </mxCell>

        <!-- ============================================================ -->
        <!-- LAYER 1: HARDWARE LAYER                                      -->
        <!-- ============================================================ -->
        <mxCell id="L1_title" value="&lt;b&gt;硬件层 (Hardware Layer)&lt;/b&gt;" style="text;html=1;align=center;verticalAlign=middle;fontSize=16;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="40" y="960" width="2320" height="30" as="geometry"/>
        </mxCell>

        <mxCell id="hw_bg" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;strokeWidth=3;opacity=30;" vertex="1" parent="1">
          <mxGeometry x="30" y="995" width="2340" height="80" as="geometry"/>
        </mxCell>

        <mxCell id="hw_mcu" value="&lt;b&gt;主控 MCU/SoC&lt;/b&gt;&lt;br&gt;ARM Cortex-R52 / M7&lt;br&gt;Multi-Core (Lockstep)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="40" y="1000" width="250" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_can" value="&lt;b&gt;CAN/CAN FD&lt;/b&gt;&lt;br&gt;Transceiver" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="300" y="1000" width="150" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_eth" value="&lt;b&gt;Ethernet PHY&lt;/b&gt;&lt;br&gt;100BASE-T1&lt;br&gt;1000BASE-T1" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="460" y="1000" width="160" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_lin" value="&lt;b&gt;LIN&lt;/b&gt;&lt;br&gt;Transceiver" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="630" y="1000" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_flash" value="&lt;b&gt;Flash / EEPROM&lt;/b&gt;&lt;br&gt;Internal + External" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="760" y="1000" width="170" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_hsm" value="&lt;b&gt;[信息安全] HSM&lt;/b&gt;&lt;br&gt;Hardware Security Module&lt;br&gt;Secure Enclave" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#D0D0FF;strokeColor=#0000CC;fontSize=11;fontColor=#0000AA;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="940" y="1000" width="220" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_wdt" value="&lt;b&gt;[功能安全] WDT HW&lt;/b&gt;&lt;br&gt;Internal + External&lt;br&gt;Window Watchdog" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFD0D0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1170" y="1000" width="210" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_mpu" value="&lt;b&gt;[功能安全] MPU/MMU&lt;/b&gt;&lt;br&gt;Memory Protection&lt;br&gt;Hardware Unit" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFD0D0;strokeColor=#CC0000;fontSize=11;fontColor=#CC0000;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="1390" y="1000" width="200" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_switch" value="&lt;b&gt;Ethernet Switch&lt;/b&gt;&lt;br&gt;TSN / VLAN" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1600" y="1000" width="160" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_sensor" value="&lt;b&gt;传感器/执行器&lt;/b&gt;&lt;br&gt;Camera / Radar&lt;br&gt;Motor / Valve" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1770" y="1000" width="190" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="hw_pmic" value="&lt;b&gt;PMIC / Power&lt;/b&gt;&lt;br&gt;电源管理 IC" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=11;" vertex="1" parent="1">
          <mxGeometry x="1970" y="1000" width="150" height="60" as="geometry"/>
        </mxCell>

        <!-- ============================================================ -->
        <!-- KEY CONNECTION ARROWS                                        -->
        <!-- ============================================================ -->

        <!-- SWC -> RTE -->
        <mxCell id="arr_swc_rte1" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#666666;" edge="1" parent="1" source="swc_powertrain" target="rte_main">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_swc_rte2" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#666666;" edge="1" parent="1" source="swc_adas" target="rte_e2e">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_swc_rte3" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#008800;" edge="1" parent="1" source="swc_dds_app" target="rte_dds_bridge">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- RTE -> BSW Services -->
        <mxCell id="arr_rte_com" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#666666;" edge="1" parent="1" source="rte_main" target="bsw_com">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_rte_e2e_lib" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#CC0000;" edge="1" parent="1" source="rte_e2e" target="bsw_e2e_lib">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_rte_dds" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#008800;" edge="1" parent="1" source="rte_dds_bridge" target="bsw_dds">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- COM -> PduR -> lower -->
        <mxCell id="arr_com_pdur" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#666666;" edge="1" parent="1" source="bsw_com" target="bsw_pdur">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_pdur_secoc" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#0000CC;" edge="1" parent="1" source="bsw_pdur" target="bsw_secoc">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- DDS -> DDS Security -->
        <mxCell id="arr_dds_sec" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#4400AA;strokeWidth=2;" edge="1" parent="1" source="bsw_dds" target="bsw_dds_sec">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- DDS -> SOME/IP Bridge -->
        <mxCell id="arr_dds_someip" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#008800;strokeWidth=2;dashed=1;" edge="1" parent="1" source="bsw_dds" target="bsw_someip">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- WdgM -> WdgIf -->
        <mxCell id="arr_wdgm_wdgif" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#CC0000;strokeWidth=2;" edge="1" parent="1" source="bsw_wdgm" target="ecu_wdgif">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- Crypto chain -->
        <mxCell id="arr_csm_cryif" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#0000CC;" edge="1" parent="1" source="bsw_csm" target="bsw_cryif">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_cryif_hsm" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#0000CC;strokeWidth=2;" edge="1" parent="1" source="bsw_cryif" target="cdd_hsm">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- SecOC -> Csm -->
        <mxCell id="arr_secoc_csm" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#0000CC;dashed=1;" edge="1" parent="1" source="bsw_secoc" target="bsw_csm">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- NvM -> MemIf -> Fee -->
        <mxCell id="arr_nvm_memif" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#666666;" edge="1" parent="1" source="bsw_nvm" target="bsw_memif">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_memif_fee" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#666666;" edge="1" parent="1" source="bsw_memif" target="ecu_fee">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- ECU Abstraction -> MCAL -->
        <mxCell id="arr_canif_can" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#666666;" edge="1" parent="1" source="ecu_canif" target="mcal_can">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_ethif_eth" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#666666;" edge="1" parent="1" source="ecu_ethif" target="mcal_eth">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- NuttX -> MCAL relationship -->
        <mxCell id="arr_nuttx_mcal" value="NuttX 通过 MCAL 或直接 HAL 访问硬件" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#D4A017;strokeWidth=2;dashed=1;fontSize=10;" edge="1" parent="1" source="nuttx_sched" target="mcal_mcu">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- HSM CDD -> HW HSM -->
        <mxCell id="arr_hsm_hw" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#0000CC;strokeWidth=2;" edge="1" parent="1" source="cdd_hsm" target="hw_hsm">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- DDS Transport -> NuttX Net -->
        <mxCell id="arr_dds_nuttx" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#008800;strokeWidth=2;" edge="1" parent="1" source="cdd_dds_transport" target="nuttx_net">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- Safe Path -> HW WDT -->
        <mxCell id="arr_safe_wdt" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#CC0000;strokeWidth=2;" edge="1" parent="1" source="cdd_safe_path" target="hw_wdt">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- MPU NuttX -> HW MPU -->
        <mxCell id="arr_nuttx_mpu_hw" style="edgeStyle=orthogonalEdgeStyle;rounded=1;strokeColor=#CC0000;strokeWidth=2;" edge="1" parent="1" source="nuttx_mpu" target="hw_mpu">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- ============================================================ -->
        <!-- LEGEND                                                       -->
        <!-- ============================================================ -->
        <mxCell id="legend_bg" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#333333;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="40" y="1090" width="900" height="100" as="geometry"/>
        </mxCell>
        <mxCell id="legend_title" value="&lt;b&gt;图例 (Legend)&lt;/b&gt;" style="text;html=1;align=left;fontSize=13;fontColor=#333333;" vertex="1" parent="1">
          <mxGeometry x="50" y="1095" width="200" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="legend_safety" value="功能安全" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=10;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="50" y="1120" width="90" height="25" as="geometry"/>
        </mxCell>
        <mxCell id="legend_security" value="信息安全" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=10;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="150" y="1120" width="90" height="25" as="geometry"/>
        </mxCell>
        <mxCell id="legend_dds" value="DDS 相关" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=10;fontColor=#006600;" vertex="1" parent="1">
          <mxGeometry x="250" y="1120" width="90" height="25" as="geometry"/>
        </mxCell>
        <mxCell id="legend_nuttx" value="NuttX 内核" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="350" y="1120" width="90" height="25" as="geometry"/>
        </mxCell>
        <mxCell id="legend_hw" value="硬件层" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="450" y="1120" width="90" height="25" as="geometry"/>
        </mxCell>
        <mxCell id="legend_std" value="标准 BSW" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="550" y="1120" width="90" height="25" as="geometry"/>
        </mxCell>
        <mxCell id="legend_dds_sec" value="DDS+信息安全" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#D0D0FF;strokeColor=#4400AA;fontSize=10;fontColor=#4400AA;" vertex="1" parent="1">
          <mxGeometry x="650" y="1120" width="100" height="25" as="geometry"/>
        </mxCell>
        <mxCell id="legend_note" value="虚线箭头 = 桥接/安全路径  |  实线箭头 = 数据流/调用" style="text;html=1;align=left;fontSize=10;fontColor=#666666;" vertex="1" parent="1">
          <mxGeometry x="50" y="1155" width="500" height="20" as="geometry"/>
        </mxCell>

      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
```

---

## 3. NuttX 与 AUTOSAR OS 的适配设计

### 3.1 总体适配策略

AUTOSAR OS (Scalability Class 3/4) 定义了一套严格的 API 和语义，包括 Task、ISR Category、Resource、Alarm、Schedule Table、OS-Application、Memory Protection 等。NuttX 作为 POSIX 兼容 RTOS，其内核机制与 AUTOSAR OS 存在映射关系但不完全对等。适配层 (**AUTOSAR OS API Shim**) 的核心职责是：

- 将 AUTOSAR OS 标准 API (`ActivateTask`, `GetResource`, `SetEvent` 等) 封装为对 NuttX POSIX API 的调用。
- 补充 NuttX 原生不提供但 AUTOSAR OS 要求的语义（如 Schedule Table 的绝对/相对同步、OS-Application 的 Trusted/Non-Trusted 划分）。
- 通过 NuttX 的 **Protected Build** 或 **Kernel Build** 模式利用 MPU/MMU 实现内存分区。

### 3.2 Task 映射

| AUTOSAR OS 概念 | NuttX 映射 | 适配细节 |
|-----------------|-----------|---------|
| **TASK (Basic)** | `pthread` 或 NuttX `task_create` | 每个 AUTOSAR Basic Task 映射为一个 NuttX 线程，通过优先级配置实现 Non-Preemptive（锁定调度器）或 Full-Preemptive（优先级抢占）语义 |
| **TASK (Extended)** | `pthread` + `eventfd` / `sigwait` | Extended Task 支持 `WaitEvent`，映射为 NuttX 的事件等待机制。使用 `eventfd` 或信号量组合模拟 AUTOSAR 事件掩码 |
| **ActivateTask** | `pthread_create` (首次) / 信号量释放 (后续) | AUTOSAR 中 Task 的多次激活通过任务队列深度控制，Shim 层维护激活计数器 |
| **ChainTask** | 当前线程终止 + 目标线程激活 | Shim 层封装为原子操作：`TerminateTask` + `ActivateTask` |
| **Schedule** | `sched_yield` | 仅在 Non-Preemptive Task 中生效，主动让出 CPU |
| **Task 优先级** | NuttX `SCHED_FIFO` 优先级 | AUTOSAR 优先级值域映射到 NuttX 的 0-255 优先级范围，需要反转映射（AUTOSAR 值越大优先级越高，NuttX 亦然） |

**AUTOSAR OS Task 状态机在 NuttX 中的实现**：

```
SUSPENDED ──ActivateTask()──→ READY ──Dispatch──→ RUNNING
    ↑                           ↑                    │
    │                           │                    │
    └──TerminateTask()──────────┘←──Preempt──────────┘
                                                     │
                                        WaitEvent()──→ WAITING
                                                     ↑     │
                                                     └──SetEvent()
```

Shim 层实现示例（伪代码）：

```c
StatusType Os_ActivateTask(TaskType TaskID) {
    OsTaskCB *tcb = &g_os_task_table[TaskID];

    nxmutex_lock(&tcb->lock);
    if (tcb->activation_count >= tcb->max_activations) {
        nxmutex_unlock(&tcb->lock);
        return E_OS_LIMIT;
    }
    tcb->activation_count++;

    if (tcb->state == SUSPENDED) {
        tcb->state = READY;
        sem_post(&tcb->start_sem);
    }
    nxmutex_unlock(&tcb->lock);
    return E_OK;
}
```

### 3.3 ISR 映射

| AUTOSAR OS 概念 | NuttX 映射 | 说明 |
|-----------------|-----------|------|
| **ISR Category 1** | NuttX `irq_attach` 直接挂载 | 不使用 OS 服务的轻量中断，直接在中断上下文执行。禁止调用任何 OS API |
| **ISR Category 2** | NuttX `irq_attach` + 下半部处理 | 中断处理分为上半部（快速 ACK + 事件标记）和下半部（通过 `work_queue` 或高优先级线程处理），可安全调用受限 OS API |
| **DisableAllInterrupts** | `up_irq_save()` | 保存并关闭全局中断 |
| **EnableAllInterrupts** | `up_irq_restore(flags)` | 恢复中断状态 |
| **SuspendOSInterrupts** | NuttX `enter_critical_section()` | 仅屏蔽 OS 管理的中断（Cat2），保留 Cat1 中断响应 |
| **ResumeOSInterrupts** | NuttX `leave_critical_section()` | 恢复 Cat2 中断 |

**Cat2 ISR 适配模式**：

```c
static int os_isr_cat2_handler(int irq, void *context, void *arg) {
    OsIsrCB *isr_cb = (OsIsrCB *)arg;

    up_disable_irq(irq);

    /* 通过高优先级工作队列延迟执行 ISR 体 */
    work_queue(HPWORK, &isr_cb->work, isr_cb->user_handler, arg, 0);

    return OK;
}
```

### 3.4 Resource 映射

| AUTOSAR OS 概念 | NuttX 映射 | 说明 |
|-----------------|-----------|------|
| **GetResource / ReleaseResource** | `pthread_mutex_lock` with Priority Ceiling | AUTOSAR Resource 使用 OSEK Priority Ceiling Protocol (立即优先级上限协议)，NuttX 通过 `PTHREAD_PRIO_PROTECT` mutex 属性实现 |
| **RES_SCHEDULER** | `sched_lock()` / `sched_unlock()` | 锁定调度器，等价于将当前任务优先级提升到最高 |
| **Internal Resource** | 任务启动时自动 `GetResource` | Shim 层在任务入口自动获取内部资源，退出时释放 |

**Priority Ceiling 配置**：

```c
void Os_InitResource(ResourceType ResID, uint8_t ceiling_prio) {
    pthread_mutexattr_t attr;
    pthread_mutexattr_init(&attr);
    pthread_mutexattr_setprotocol(&attr, PTHREAD_PRIO_PROTECT);
    pthread_mutexattr_setprioceiling(&attr, ceiling_prio);
    pthread_mutex_init(&g_os_resources[ResID].mutex, &attr);
}
```

### 3.5 Alarm 映射

| AUTOSAR OS 概念 | NuttX 映射 | 说明 |
|-----------------|-----------|------|
| **Alarm (单次)** | `timer_settime` (POSIX Timer, 非周期) | 使用 `CLOCK_MONOTONIC` 创建 POSIX Timer，到期后回调通知 Shim 层 |
| **Alarm (周期)** | `timer_settime` (带 `it_interval`) | 设置周期 interval 实现自动重装 |
| **Alarm Action: ActivateTask** | Timer 回调中调用 `Os_ActivateTask` | 在 signal handler 或定时器线程中触发 |
| **Alarm Action: SetEvent** | Timer 回调中调用 `Os_SetEvent` | 唤醒等待事件的 Extended Task |
| **Alarm Action: Callback** | Timer 回调中直接执行用户函数 | 需注意回调上下文限制 |
| **Counter** | NuttX `CLOCK_MONOTONIC` tick 或硬件计数器 | 每个 AUTOSAR Counter 映射为一个 NuttX 时钟源 |

```c
StatusType Os_SetRelAlarm(AlarmType AlarmID, TickType increment, TickType cycle) {
    struct itimerspec its;
    OsAlarmCB *alarm = &g_os_alarm_table[AlarmID];

    its.it_value.tv_sec  = increment / alarm->ticks_per_sec;
    its.it_value.tv_nsec = (increment % alarm->ticks_per_sec) *
                           (1000000000UL / alarm->ticks_per_sec);
    its.it_interval.tv_sec  = cycle / alarm->ticks_per_sec;
    its.it_interval.tv_nsec = (cycle % alarm->ticks_per_sec) *
                              (1000000000UL / alarm->ticks_per_sec);

    return timer_settime(alarm->posix_timer, 0, &its, NULL) == 0
           ? E_OK : E_OS_STATE;
}
```

### 3.6 Schedule Table 映射

Schedule Table 是 AUTOSAR OS 中用于同步驱动多个 Expiry Point 的机制，比单独 Alarm 更适合周期性多任务协调（如 1ms/5ms/10ms 任务组）。

**实现方案**：

1. 每个 Schedule Table 对应一个专用 NuttX 高优先级线程（`sched_table_thread`）。
2. 线程内维护 Expiry Point 列表，按偏移量排序。
3. 使用 `clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, ...)` 精确等待到下一个 Expiry Point。
4. 到期后依次执行 `ActivateTask` 或 `SetEvent` 动作。

**同步支持**：

- **隐式同步 (Implicit)**: Schedule Table 启动即视为同步。
- **显式同步 (Explicit)**: 通过外部同步源（如全局时间 Global Time Master）校准。Shim 层提供 `Os_SyncScheduleTable(ScheduleTableID, GlobalTime)` 接口，在线程中动态调整下一个 Expiry Point 的等待时间以消除偏差。

```c
static void *sched_table_thread(void *arg) {
    OsSchedTableCB *st = (OsSchedTableCB *)arg;
    struct timespec next_abs;

    clock_gettime(CLOCK_MONOTONIC, &next_abs);

    while (st->state == SCHEDULETABLE_RUNNING) {
        for (int i = 0; i < st->num_expiry_points; i++) {
            timespec_add_ticks(&next_abs, st->expiry[i].offset);
            clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, &next_abs, NULL);

            for (int j = 0; j < st->expiry[i].num_actions; j++) {
                execute_expiry_action(&st->expiry[i].actions[j]);
            }
        }
        /* 周期表: 回到起始 offset, 继续循环 */
        if (!st->is_repeating) break;
    }
    return NULL;
}
```

### 3.7 内存保护与分区隔离 (MPU/MMU)

#### 3.7.1 NuttX Build Mode 选择

| Build Mode | 说明 | 适用场景 |
|-----------|------|---------|
| **Flat Build** | 所有代码运行在同一地址空间，无保护 | 仅用于开发阶段 |
| **Protected Build** | 内核态 (Kernel) + 用户态 (User)，MPU 隔离 | **推荐用于区域控制器 (ZC)**，Cortex-M/R 平台 |
| **Kernel Build** | 完整 MMU 支持，进程隔离 | **推荐用于中央计算单元 (CCU)**，Cortex-A 平台 |

#### 3.7.2 AUTOSAR OS-Application 到 NuttX 分区映射

```
┌─────────────────────────────────────────────────────────┐
│                    NuttX Kernel Space                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ OS Shim  │  │ BSW Core │  │ Trusted OS-App       │   │
│  │ Layer    │  │ Services │  │ (Safety Critical)    │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│                    NuttX User Space                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐     │
│  │ Non-Trusted│  │ Non-Trusted│  │ Non-Trusted    │     │
│  │ OS-App #1  │  │ OS-App #2  │  │ OS-App #3      │     │
│  │ (Body SWC) │  │ (Info SWC) │  │ (Third-Party)  │     │
│  │ MPU Rgn #1 │  │ MPU Rgn #2 │  │ MPU Rgn #3     │     │
│  └────────────┘  └────────────┘  └────────────────┘     │
└─────────────────────────────────────────────────────────┘
```

**分区策略**：

- **Trusted OS-Application**：安全关键 SWC（动力、底盘、WdgM 回调）运行在内核空间或高权限分区，直接访问 BSW 服务。
- **Non-Trusted OS-Application**：车身、信息娱乐、第三方 SWC 运行在用户空间，通过系统调用 (syscall) 访问 BSW。
- **MPU Region 配置**：每个 Non-Trusted OS-Application 分配独立的 MPU Region，包含代码段 (RX)、数据段 (RW)、栈 (RW+NX) 和共享数据段 (R 或 RW，按需)。

**NuttX MPU 配置 (ARM Cortex-R52 示例)**：

```c
struct mpu_region_s os_app_regions[MAX_OS_APPLICATIONS][MAX_REGIONS_PER_APP] = {
    [OS_APP_BODY] = {
        { .base = 0x20010000, .size = 0x4000,  /* .text */
          .flags = MPU_RASR_AP_RORO | MPU_RASR_XN_DISABLE },
        { .base = 0x20014000, .size = 0x2000,  /* .data + .bss */
          .flags = MPU_RASR_AP_RWRW | MPU_RASR_XN_ENABLE },
        { .base = 0x20016000, .size = 0x1000,  /* stack */
          .flags = MPU_RASR_AP_RWRW | MPU_RASR_XN_ENABLE },
    },
};

void os_switch_partition(OsApplicationType app_id) {
    mpu_configure_regions(os_app_regions[app_id],
                          os_app_region_count[app_id]);
}
```

### 3.8 时间保护与 WdgM 联动

#### 3.8.1 时间保护机制

AUTOSAR OS 要求对 Task 和 Cat2 ISR 实施执行时间预算 (Execution Budget) 监控：

1. **Execution Budget**：任务/ISR 在一个周期内的最大允许执行时间。
2. **Time Limit**：任务锁定资源 (GetResource) 的最大持有时间。
3. **Inter-Arrival Time**：同一任务两次激活之间的最小间隔。

**NuttX 实现方案**：

- 利用 NuttX 的 `CLOCK_MONOTONIC` 高精度时钟，在 Shim 层 Task 入口/出口记录时间戳。
- 使用独立硬件定时器 (GPT) 设置 Deadline 中断，超时触发 `ProtectionHook`。
- `ProtectionHook` 根据配置执行: `PRO_TERMINATETASKISR` / `PRO_TERMINATEAPPL` / `PRO_TERMINATEAPPL_RESTART` / `PRO_SHUTDOWN`。

```c
void Os_TaskEntryHook(TaskType TaskID) {
    OsTaskCB *tcb = &g_os_task_table[TaskID];
    clock_gettime(CLOCK_MONOTONIC, &tcb->exec_start);

    /* 配置硬件定时器作为 deadline 监控 */
    struct itimerspec budget_timer = {
        .it_value.tv_nsec = tcb->execution_budget_ns,
    };
    timer_settime(tcb->budget_timer_id, 0, &budget_timer, NULL);
}

void Os_TaskExitHook(TaskType TaskID) {
    /* 取消 budget 定时器 */
    struct itimerspec disarm = { 0 };
    timer_settime(g_os_task_table[TaskID].budget_timer_id, 0, &disarm, NULL);
}

static void budget_timeout_handler(union sigval sv) {
    TaskType task_id = (TaskType)sv.sival_int;
    StatusType action = ProtectionHook(E_OS_PROTECTION_TIME);
    execute_protection_action(action, task_id);
}
```

#### 3.8.2 与 WdgM 的分层联动

```
┌──────────────────────────────────────────────────┐
│           WdgM (Watchdog Manager)                 │
│  ┌──────────┐ ┌──────────┐ ┌───────────────┐    │
│  │ Alive    │ │ Deadline │ │ Logical       │    │
│  │ Superv.  │ │ Superv.  │ │ Supervision   │    │
│  └────┬─────┘ └────┬─────┘ └──────┬────────┘    │
│       │             │              │              │
│  ┌────▼─────────────▼──────────────▼────────┐    │
│  │      Supervised Entity (SE) 状态机        │    │
│  │  OK → DEACTIVATED / EXPIRED / FAILED     │    │
│  └─────────────────┬────────────────────────┘    │
│                    │                              │
│  ┌─────────────────▼────────────────────────┐    │
│  │   Global Status: OK / FAILED / EXPIRED    │    │
│  │   → Trigger Mode (WdgIf) 或 Safe State    │    │
│  └───────────────────────────────────────────┘    │
└──────────────────────────────────────────────────┘
        │                              │
        ▼                              ▼
   WdgIf → Wdg Driver            Safe State Manager
   (喂狗/停止喂狗)              (安全关断路径)
```

- **Alive Supervision**：SWC 在每个周期调用 `WdgM_CheckpointReached(SE_ID, CP_ID)`，WdgM 检查调用频率是否在 `[min, max]` 窗口内。Shim 层在每次 `Os_TerminateTask` 时自动插入 Checkpoint。
- **Deadline Supervision**：监控两个 Checkpoint 之间的时间间隔。结合 NuttX 时间保护的 `exec_start` 时间戳实现。
- **Logical Supervision**：校验 Checkpoint 序列是否符合预定义的有向图 (DAG)，检测程序流异常。

### 3.9 多核调度策略

#### 3.9.1 平台架构分型

| 节点类型 | 处理器示例 | 多核模式 | NuttX 部署 |
|---------|-----------|---------|-----------|
| **CCU (中央计算单元)** | ARM Cortex-A76 + Cortex-R52 | AMP (Jailhouse Hypervisor) | NuttX on R52 (Safety Island)，Linux on A76 |
| **ZC (区域控制器)** | ARM Cortex-R52 Dual-Core | SMP (NuttX 原生) | 双核 NuttX SMP，或 Lockstep 模式 |
| **传感器节点** | ARM Cortex-M7 | Single Core | NuttX Flat/Protected Build |

#### 3.9.2 SMP 调度 (NuttX 原生支持)

NuttX 自 12.x 版本起完整支持 SMP，关键配置：

```
CONFIG_SMP=y
CONFIG_SMP_NCPUS=2
CONFIG_SMP_IDLETHREAD_STACKSIZE=2048
```

- **CPU Affinity**：安全关键任务绑定到指定核心，通过 `sched_setaffinity` 或 `pthread_attr_setaffinity_np` 设置。
- **自旋锁**：核间共享资源使用 `spin_lock_irqsave` / `spin_unlock_irqrestore`。
- **AUTOSAR OS 映射**：每个 OS-Application 可绑定到指定 Core，Shim 层在 `ActivateTask` 时根据 Task 所属 OS-Application 设置 CPU Affinity。

#### 3.9.3 AMP 隔离方案 (安全核 vs. 性能核)

```
┌───────────────────────────────────────────────────────────┐
│                     CCU Hardware                           │
│  ┌─────────────────────┐    ┌──────────────────────────┐  │
│  │  Cortex-A76 Cluster  │    │  Cortex-R52 (Safety)     │  │
│  │  ┌────────────────┐  │    │  ┌──────────────────────┐│  │
│  │  │   Linux / QNX   │  │    │  │  NuttX + AUTOSAR BSW ││  │
│  │  │   ADAS / HMI    │  │    │  │  Safety-Critical SWC ││  │
│  │  │   DDS Runtime   │  │    │  │  WdgM / E2E / SecOC  ││  │
│  │  └────────────────┘  │    │  └──────────────────────┘│  │
│  └──────────┬───────────┘    └────────────┬─────────────┘  │
│             │         OpenAMP / RPMsg      │                │
│             └──────────────────────────────┘                │
│                    Shared Memory (SRAM)                      │
│                    Jailhouse Hypervisor                      │
└───────────────────────────────────────────────────────────┘
```

- **Jailhouse Hypervisor**：静态分区虚拟机管理器，将 R52 核心完全隔离为独立 Cell，运行 NuttX + AUTOSAR BSW，满足 ASIL-D 要求。
- **OpenAMP / RPMsg**：NuttX 原生支持 OpenAMP，通过 `rpmsg_char` 和 `rpmsg_socket` 实现核间通信。AUTOSAR SWC 在安全核产生的数据通过 RPMsg 传输到性能核上的 DDS/SOME/IP 发布。
- **内存隔离**：Jailhouse 通过 SMMU/MPU 配置确保安全核与性能核的物理内存完全隔离，仅共享 RPMsg 通信区域。

---

## 4. BSW 关键模块集成策略

### 4.1 通信栈

#### 4.1.1 传统总线: CAN/CAN FD

```
┌─────────┐
│   COM    │  Signal-level Tx/Rx
├─────────┤
│  PduR   │  PDU Routing (Fan-in / Fan-out)
├─────────┤
│  CanTp  │  CAN Transport Protocol (ISO 15765)
├─────────┤
│  CanIf  │  CAN Interface (Tx Confirmation, Rx Indication)
├─────────┤
│  NuttX  │  SocketCAN 或 character device (/dev/can0)
├─────────┤
│  MCAL   │  Can Driver (寄存器级别操作, MCAN/FlexCAN)
├─────────┤
│   HW    │  CAN Controller + Transceiver
└─────────┘
```

**NuttX 集成要点**：

- NuttX 提供 SocketCAN 支持 (`CONFIG_NET_CAN=y`)，CanIf 可直接通过 `socket(AF_CAN, SOCK_RAW, CAN_RAW)` 接口收发 CAN 帧。
- 对于资源受限场景，也可使用 NuttX 的 character device 驱动 (`/dev/can0`)，CanIf 通过 `ioctl` 接口配置波特率、过滤器等。
- CAN FD 支持通过 `CAN_RAW_FD_FRAMES` socket option 或扩展 ioctl 启用。

**MCAL Can Driver 适配**：

```c
/* NuttX CAN 底层驱动注册 */
static const struct can_ops_s g_mcan_ops = {
    .co_reset    = mcan_reset,
    .co_setup    = mcan_setup,
    .co_shutdown = mcan_shutdown,
    .co_txready  = mcan_txready,
    .co_send     = mcan_send,
    .co_rxint    = mcan_rxint,
    .co_txint    = mcan_txint,
    .co_ioctl    = mcan_ioctl,
};

void mcal_can_init(void) {
    struct can_dev_s *dev = mcan_initialize(0);
    can_register("/dev/can0", dev);
}
```

#### 4.1.2 LIN 协议栈

```
COM → PduR → LinTp → LinIf → NuttX UART (/dev/ttyS1) → MCAL Lin Driver → HW
```

- LIN Master 节点的 Schedule Table 由 LinIf 管理，通过 NuttX UART 接口发送/接收 LIN 帧。
- LinIf 的 `Lin_SendFrame` / `Lin_GetStatus` 映射为 NuttX UART 的 `write` / `read` + 定时控制。
- LIN 的 Break/Sync/PID 时序通过 UART LIN 模式（如 STM32 USART LIN Mode）或 GPIO bit-bang 实现。

#### 4.1.3 车载以太网: TCP/IP + SOME/IP

**TCP/IP 协议栈对接**：

NuttX 内置完整的 TCP/IP 协议栈，AUTOSAR TcpIp 模块直接复用：

```
┌────────────┐
│   SoAd     │  Socket Adaptor (AUTOSAR BSW ↔ BSD Socket 适配)
├────────────┤
│  TcpIp     │  ≡ NuttX TCP/IP Stack (BSD Socket API)
│            │  CONFIG_NET_TCP=y, CONFIG_NET_UDP=y
│            │  CONFIG_NET_IPv4=y, CONFIG_NET_IPv6=y
├────────────┤
│   EthIf    │  Ethernet Interface (VLAN Tag, Priority)
├────────────┤
│  NuttX     │  Ethernet Driver (netdev, DMA ring buffer)
├────────────┤
│  MCAL Eth  │  Eth Driver (MAC register + PHY MDIO)
└────────────┘
```

**SoAd (Socket Adaptor)** 是 AUTOSAR BSW 与 BSD Socket 的关键适配层：

```c
Std_ReturnType SoAd_OpenSoCon(SoAd_SoConIdType SoConId) {
    SoAd_SocketCfg *cfg = &SoAd_Config.connections[SoConId];
    int sock = socket(AF_INET, cfg->protocol == TCPIP_IPPROTO_TCP
                      ? SOCK_STREAM : SOCK_DGRAM, 0);

    struct sockaddr_in addr = {
        .sin_family = AF_INET,
        .sin_port   = htons(cfg->local_port),
        .sin_addr.s_addr = htonl(cfg->local_addr),
    };
    bind(sock, (struct sockaddr *)&addr, sizeof(addr));

    if (cfg->protocol == TCPIP_IPPROTO_TCP && cfg->is_server) {
        listen(sock, cfg->max_connections);
    }

    cfg->nuttx_fd = sock;
    return E_OK;
}
```

**SOME/IP 部署**：

选择轻量级 SOME/IP 实现（如 **vSomeIP** 的嵌入式精简版或 **SOME/IP 自研栈**）：

- vSomeIP 核心库约 200KB Flash，可在 NuttX 上编译运行。
- SOME/IP-SD (Service Discovery) 使用 UDP 组播 (239.x.x.x:30490)，通过 NuttX `setsockopt(IP_ADD_MEMBERSHIP)` 加入组播组。
- SOME/IP Serialization/Deserialization 在 RTE 的 SOME/IP Transformer 中完成。
- 考虑到 NuttX 平台资源限制，建议对 vSomeIP 进行裁剪：移除 Boost 依赖，使用 NuttX POSIX API 替代。

#### 4.1.4 DDS 集成

##### DDS 实现选型

| 实现 | Flash 占用 | RAM 占用 | NuttX 兼容性 | 推荐场景 |
|-----|-----------|---------|-------------|---------|
| **Cyclone DDS** (Eclipse) | ~300KB | ~50KB | 良好 (POSIX) | CCU + ZC 通用 |
| **Micro-XRCE-DDS** (eProsima) | ~50KB | ~10KB | 优秀 (轻量) | 资源受限 ZC |
| **Fast DDS** (eProsima) | ~800KB | ~100KB | 需裁剪 | CCU 高性能场景 |

**推荐方案**：

- **CCU**: Cyclone DDS (完整 RTPS 协议栈)
- **ZC**: Micro-XRCE-DDS (Agent 运行在 CCU 上，Client 运行在 ZC 上)

##### DDS 在 BSW 通信服务层的位置

```
┌──────────────────────────────────────────────────────────┐
│                    BSW Communication Services              │
│                                                            │
│  ┌─────────┐    ┌──────────┐    ┌──────────────────────┐  │
│  │  COM    │    │  PduR    │    │  DDS Middleware       │  │
│  │(Signal) │    │(PDU路由) │    │  ┌────────────────┐  │  │
│  └────┬────┘    └────┬─────┘    │  │ RTPS Protocol  │  │  │
│       │              │          │  │ Discovery      │  │  │
│       │              │          │  │ QoS Policies   │  │  │
│       └──────┬───────┘          │  └────────────────┘  │  │
│              │                  └──────────┬───────────┘  │
│              │                             │              │
│    ┌─────────▼─────────────────────────────▼───────────┐  │
│    │         DDS-SOME/IP Bridge (Protocol Gateway)     │  │
│    │  PDU ↔ DDS Topic 映射  |  QoS ↔ Priority 映射    │  │
│    │  Serialization 转换     |  Service ↔ Topic 映射   │  │
│    └───────────────────────────────────────────────────┘  │
│              │                             │              │
│       ┌──────▼──────┐            ┌─────────▼──────────┐  │
│       │  SOME/IP    │            │  DDS Transport     │  │
│       │  (vsomeip)  │            │  (UDP Multicast)   │  │
│       └──────┬──────┘            │  (Shared Memory)   │  │
│              │                   └─────────┬──────────┘  │
│              └──────────┬──────────────────┘              │
│                         ▼                                 │
│                  SoAd / NuttX Socket API                   │
└──────────────────────────────────────────────────────────┘
```

##### DDS-SOME/IP 桥接模块设计

桥接模块 (`DdsSomeipBridge`) 是实现 DDS 与传统 AUTOSAR 通信共存的关键组件：

```c
typedef struct {
    const char      *dds_topic_name;
    const char      *dds_type_name;
    uint16_t         someip_service_id;
    uint16_t         someip_method_id;
    PduIdType        autosar_pdu_id;
    SerializerFunc   dds_to_someip;
    DeserializerFunc someip_to_dds;
    dds_qos_t       *qos_profile;
} DdsSomeipBridgeEntry;

static const DdsSomeipBridgeEntry g_bridge_table[] = {
    {
        .dds_topic_name   = "Vehicle/Chassis/WheelSpeed",
        .dds_type_name    = "WheelSpeedType",
        .someip_service_id = 0x1234,
        .someip_method_id  = 0x0001,
        .autosar_pdu_id    = PduConf_WheelSpeed_Tx,
        .dds_to_someip     = WheelSpeed_DdsToSomeip,
        .someip_to_dds     = WheelSpeed_SomeipToDds,
        .qos_profile       = &qos_reliable_10ms,
    },
};
```

**DDS 向 RTE 提供 Topic 发布/订阅**：

通过 `DDS-RTE Bridge` 模块，DDS Topic 被映射为 AUTOSAR Sender-Receiver Port：

1. **配置阶段**：AUTOSAR 工具链中定义 DDS-backed Port，生成 RTE 代码时插入 DDS API 调用而非 COM API。
2. **运行时**：SWC 调用 `Rte_Read_<port>` 时，RTE 内部调用 `dds_read()` 从 DDS DataReader 获取最新样本。
3. **QoS 映射**：DDS QoS Profile (Reliability, Deadline, Liveliness) 映射为 AUTOSAR 的通信超时、E2E 保护参数。

```c
Std_ReturnType Rte_Read_SWC_Chassis_WheelSpeed(WheelSpeedType *data) {
    dds_sample_info_t info;
    int ret = dds_take(g_wheel_speed_reader, (void **)&data, &info, 1, 1);

    if (ret > 0 && info.valid_data) {
        return RTE_E_OK;
    }
    return RTE_E_NO_DATA;
}
```

### 4.2 诊断栈

```
┌────────────────────────────────────────────────────────────┐
│  Dcm (Diagnostic Communication Manager)                     │
│  ├── UDS Services: 0x10 (Session), 0x27 (SecurityAccess),  │
│  │   0x22/0x2E (DID R/W), 0x14/0x19 (DTC), 0x31 (Routine) │
│  │   0x29 (Authentication), 0x34-0x37 (Download/Upload)    │
│  └── Protocol: DoIP (TCP), DoCAN (ISO-TP)                   │
├────────────────────────────────────────────────────────────┤
│  Dem (Diagnostic Event Manager)                              │
│  ├── DTC Storage (Primary/Secondary/Mirror Memory)          │
│  ├── Event Debounce (Counter/Timer-based)                   │
│  ├── Aging / Displacement                                    │
│  └── Snapshot (Freeze Frame) + Extended Data Records        │
├────────────────────────────────────────────────────────────┤
│  DoIP (ISO 13400)                                            │
│  ├── Vehicle Identification (UDP Broadcast)                  │
│  ├── Diagnostic Message (TCP)                                │
│  ├── Routing Activation                                      │
│  └── ≡ NuttX TCP/UDP Socket (SoAd 层)                       │
└────────────────────────────────────────────────────────────┘
```

**DoIP 与 NuttX 网络栈的关系**：

- DoIP 的 Vehicle Identification 使用 UDP 广播/组播，通过 NuttX 的 `sendto(INADDR_BROADCAST)` 实现。
- Diagnostic Message 使用 TCP 长连接，NuttX 的 `select/poll` 机制处理多连接并发。
- TLS 支持（DoIP 安全传输）通过 NuttX 集成的 **mbedTLS** (`CONFIG_CRYPTO_MBEDTLS=y`) 实现。

### 4.3 网络管理

AUTOSAR NM (Network Management) 通过协调 ECU 的通信状态实现总线休眠/唤醒管理：

- **CanNm**: 基于 CAN 的 NM，周期性发送 NM PDU，通过 NuttX CAN 接口收发。
- **UdpNm**: 基于 UDP 的 NM，用于车载以太网，通过 NuttX UDP Socket 收发。
- **Partial Networking (PN)**: 支持选择性唤醒，CAN Transceiver 的 PN 功能通过 MCAL CanTrcv Driver 的 SPI/GPIO 接口配置。

**NM 状态机**：

```
Bus-Sleep ──(NM-Request)──→ Repeat Message ──(Timer)──→ Normal Operation
    ↑                                                         │
    └──(NM-Timeout)──← Ready Sleep ←──(Release Network)──────┘
```

- NM 定时器 (Repeat Message Timer, NM Timeout, Wait Bus Sleep Timer) 使用 NuttX POSIX Timer 实现。
- `ComM` 协调 NM 与 COM 的模式切换：`FULL_COMMUNICATION` / `SILENT_COMMUNICATION` / `NO_COMMUNICATION`。

### 4.4 存储栈

```
┌──────────┐
│   NvM    │  Block-based NVRAM Management
│          │  Read/Write/Invalidate/Restore
│          │  CRC Verification, Redundant Blocks
├──────────┤
│  MemIf   │  Abstraction: Fee (Flash) / EA (EEPROM)
├──────────┤
│  Fee     │  Flash EEPROM Emulation
│          │  Wear Leveling, Garbage Collection
├──────────┤
│ NuttX FS │  方案A: MTD + LittleFS → /dev/nvram
│  or Raw  │  方案B: Raw Flash → MCAL Fls Driver
├──────────┤
│ MCAL Fls │  Flash Driver (Program/Erase/Read)
└──────────┘
```

**两种实现路径**：

| 路径 | 说明 | 优点 | 缺点 |
|-----|------|-----|-----|
| **Path A: NuttX FS** | Fee 基于 NuttX 的 LittleFS/FAT 文件系统，每个 NvM Block 映射为一个文件 | 利用 NuttX 成熟的文件系统和 MTD 框架，开发快 | 额外文件系统开销 |
| **Path B: Raw Flash** | Fee 直接通过 MCAL Fls Driver 操作 Raw Flash Sector | 与传统 AUTOSAR 实现一致，性能可控 | 需自行实现磨损均衡 |

**推荐**：ZC 使用 Path B (资源受限)，CCU 使用 Path A (存储需求大)。

NvM Block 配置示例：

```c
const NvM_BlockDescriptorType NvM_BlockDescriptor[] = {
    [NvMConf_NvMBlockDescriptor_DTC_Primary] = {
        .NvMBlockLength       = 4096,
        .NvMBlockManagementType = NVM_BLOCK_REDUNDANT,
        .NvMBlockCrcType      = NVM_CRC32,
        .NvMRamBlockDataAddress = &Dem_DTCPrimaryMirror,
        .NvMRomBlockDataAddress = &Dem_DTCPrimaryDefault,
        .NvMWriteBlockOnce    = FALSE,
        .NvMResistantToChangedSw = TRUE,
    },
};
```

### 4.5 系统服务

#### 4.5.1 EcuM (ECU State Manager)

EcuM 管理 ECU 的启动、运行和关断生命周期，与 NuttX 的启动流程集成：

```
Power-On
  │
  ▼
NuttX Boot (board_initialize)
  │
  ▼
EcuM_Init()
  ├── Mcu_Init, Port_Init, Dio_Init (MCAL 初始化)
  ├── Os_Init → NuttX 内核已在 board_initialize 中启动
  ├── SchM_Init (BSW Scheduler)
  └── BswM_Init
  │
  ▼
EcuM_StartupTwo()
  ├── 通信栈初始化 (ComM, NM, COM, CanIf, EthIf...)
  ├── 诊断栈初始化 (Dcm, Dem, DoIP...)
  ├── 安全栈初始化 (WdgM, Csm, SecOC...)
  ├── DDS 中间件初始化 (dds_init, domain participant 创建)
  └── RTE_Start()
  │
  ▼
RUN State
  ├── SWC Runnables 执行
  ├── BSW MainFunctions 周期调用 (SchM)
  └── 等待 EcuM_GoDown / EcuM_GoHalt / Sleep Request
  │
  ▼
SHUTDOWN / SLEEP
  ├── EcuM_GoDown: 关闭通信 → 保存 NvM → 复位
  └── EcuM_GoHalt: 低功耗模式 → NuttX pm_sleep()
```

#### 4.5.2 BswM (BSW Mode Manager)

BswM 基于规则引擎 (Rule-based) 管理系统模式切换：

```c
/* BswM 规则示例: 当 ComM 进入 FULL_COMMUNICATION 时，启用 COM 和 NM */
const BswM_RuleType BswM_Rules[] = {
    {
        .condition = BSWM_COND_COMM_FULL_COMM,
        .actions = {
            { BSWM_ACT_COM_ALLOW_COMM, TRUE },
            { BSWM_ACT_NM_ENABLE, TRUE },
            { BSWM_ACT_PDUR_ENABLE_ROUTING, PduR_RoutingGroup_CAN },
            { BSWM_ACT_DDS_START_PARTICIPANT, DDS_Domain_Vehicle },
        },
    },
    {
        .condition = BSWM_COND_ECUM_SHUTDOWN,
        .actions = {
            { BSWM_ACT_NVM_WRITE_ALL, TRUE },
            { BSWM_ACT_DDS_STOP_PARTICIPANT, DDS_Domain_Vehicle },
            { BSWM_ACT_COM_DISABLE_COMM, TRUE },
        },
    },
};
```

#### 4.5.3 WdgM 设计

详见 [3.8 节](#38-时间保护与-wdgm-联动)。WdgM 的配置通过 AUTOSAR 工具链生成，包含所有 Supervised Entity、Checkpoint 和 Transition 的定义。

#### 4.5.4 SchM (BSW Scheduler)

SchM 负责触发 BSW 模块的 `MainFunction` 周期执行：

```c
/* SchM 使用 NuttX 周期定时器驱动 BSW MainFunction 调用 */
static void schm_1ms_task(void *arg) {
    Com_MainFunctionTx();
    Com_MainFunctionRx();
}

static void schm_5ms_task(void *arg) {
    CanSM_MainFunction();
    PduR_MainFunction();
    SecOC_MainFunctionTx();
    SecOC_MainFunctionRx();
}

static void schm_10ms_task(void *arg) {
    Dcm_MainFunction();
    Dem_MainFunction();
    NvM_MainFunction();
    WdgM_MainFunction();
    BswM_MainFunction();
    EcuM_MainFunction();
    DdsBridge_MainFunction();
}
```

### 4.6 复杂驱动 (CDD)

#### 4.6.1 与 NuttX 设备驱动模型的对接

NuttX 使用 VFS + devfs 模型，所有设备通过 `/dev/xxx` 路径访问。CDD 模块注册为 NuttX 字符设备驱动或块设备驱动：

```c
/* CDD 传感器融合模块注册为字符设备 */
static const struct file_operations g_sensor_fusion_fops = {
    .open  = sensor_fusion_open,
    .close = sensor_fusion_close,
    .read  = sensor_fusion_read,
    .write = sensor_fusion_write,
    .ioctl = sensor_fusion_ioctl,
};

void cdd_sensor_fusion_init(void) {
    register_driver("/dev/sensor_fusion0", &g_sensor_fusion_fops,
                    0666, &g_sensor_ctx);
}
```

BSW 上层通过标准 POSIX 接口 (`open/read/write/ioctl`) 访问 CDD：

```c
int fd = open("/dev/sensor_fusion0", O_RDWR);
ioctl(fd, SENSOR_FUSION_CMD_GET_OBJECT_LIST, &object_list);
```

#### 4.6.2 DDS 作为复杂驱动集成

当 DDS 需要绕过标准 AUTOSAR COM 栈直接处理高带宽数据（如点云、图像）时，可将 DDS Transport 封装为 CDD：

```
SWC (Perception)
    │
    ▼ (CDD Port)
CDD_DDS_Lidar ──→ DDS DataWriter ──→ RTPS ──→ NuttX UDP Socket ──→ Ethernet
    │
    ▼ (devfs)
/dev/dds_lidar0 (NuttX 字符设备)
```

---

## 5. 功能安全与信息安全的具体落地方案

### 5.1 功能安全 (ISO 26262)

#### 5.1.1 内存分区与 MPU 保护机制

**目标**：实现 ASIL-D 级别的 Freedom from Interference (FFI)。

**分区策略**：

| 分区 | 内容 | ASIL | MPU 权限 | NuttX Build |
|-----|------|------|---------|-------------|
| **P0 (Kernel)** | NuttX 内核 + OS Shim + SchM | QM (已验证基础设施) | Full Access | Kernel Space |
| **P1 (Safety BSW)** | WdgM, E2E, Dem(Safety), BswM(Safety) | ASIL-D | RWX (Kernel) | Trusted OS-App |
| **P2 (Comm BSW)** | COM, PduR, CanIf, EthIf, SecOC | ASIL-B | RWX (Kernel) | Trusted OS-App |
| **P3 (Safety SWC)** | 动力控制, ESP, EPS | ASIL-D | RW (User) | Non-Trusted + MPU |
| **P4 (QM SWC)** | 车身控制, HVAC | QM | RW (User) | Non-Trusted + MPU |
| **P5 (Third Party)** | OTA, 第三方 SWC | QM | RW (User, Strict) | Non-Trusted + MPU |

**MPU 违例处理**：

```c
void up_mpufault(void *context) {
    uint32_t fault_addr = getreg32(SCB_MMFAR);
    TaskType task_id = Os_GetCurrentTask();
    OsApplicationType app_id = Os_GetTaskApplication(task_id);

    Dem_ReportErrorStatus(DemConf_MPU_Violation, DEM_EVENT_STATUS_FAILED);
    WdgM_ReportSupervisionError(app_id);

    StatusType action = ProtectionHook(E_OS_PROTECTION_MEMORY);
    switch (action) {
        case PRO_TERMINATETASKISR:
            Os_TerminateTask(task_id);
            break;
        case PRO_TERMINATEAPPL:
            Os_TerminateApplication(app_id, NO_RESTART);
            break;
        case PRO_TERMINATEAPPL_RESTART:
            Os_TerminateApplication(app_id, RESTART);
            break;
        case PRO_SHUTDOWN:
            EcuM_PerformReset(ECUM_RESET_MCU);
            break;
    }
}
```

#### 5.1.2 E2E 保护注入点

E2E (End-to-End) 保护根据 AUTOSAR E2E Library 的 Profile 定义，在通信路径中插入 CRC、Counter、Data ID 等校验信息，检测通信链路上的数据损坏、丢失、延迟等故障。

**注入点位置选择**：

```
方案A: RTE 层注入 (推荐用于 S/R 通信)
SWC → [RTE E2E Transformer] → COM → PduR → ...
       ▲ CRC计算 + Counter递增

方案B: COM 层注入 (推荐用于 Gateway ECU)
... → PduR → [COM + E2E Wrapper] → PduR → ...
              ▲ 转发时保持 E2E 信息
```

**E2E Profile 选型指南**：

| Profile | CRC | Counter | 适用场景 |
|---------|-----|---------|---------|
| **Profile 1** | CRC-8 | 4-bit | CAN 经典帧 (8 字节) |
| **Profile 2** | CRC-8 | 4-bit | FlexRay |
| **Profile 4** | CRC-32 | 16-bit | 长 PDU (CAN FD / Ethernet) |
| **Profile 5** | CRC-32 | 8-bit | 中等长度 PDU |
| **Profile 7** | CRC-64 | 32-bit | 以太网大载荷 (>1KB) |

**RTE E2E Transformer 实现**：

```c
Std_ReturnType E2E_Protect_Profile4(
    E2E_P04ProtectStateType *state,
    const E2E_P04ConfigType *config,
    uint8_t *data, uint32_t length)
{
    /* 写入 Counter (16-bit, offset=8) */
    uint16_t counter = state->Counter;
    data[config->CounterOffset]     = (uint8_t)(counter >> 8);
    data[config->CounterOffset + 1] = (uint8_t)(counter);

    /* 写入 Data ID (16-bit, offset=12) */
    data[config->DataIDOffset]     = (uint8_t)(config->DataID >> 8);
    data[config->DataIDOffset + 1] = (uint8_t)(config->DataID);

    /* 计算并写入 CRC-32 (offset=0) */
    uint32_t crc = Crc_CalculateCRC32P4(data + 4, length - 4, 0xFFFFFFFF, TRUE);
    memcpy(&data[0], &crc, 4);

    state->Counter++;
    return E_OK;
}
```

#### 5.1.3 程序流监控与安全关断路径

**程序流监控 (Logical Supervision)**：

WdgM 的 Logical Supervision 通过检查 Checkpoint 序列是否符合预定义图来检测控制流异常：

```
定义图 (以 ESP 控制为例):
CP_Init → CP_SensorRead → CP_Algorithm → CP_ActuatorCmd → CP_Done
                ↓ (异常分支)
           CP_SafeState (安全状态)
```

```c
/* SWC 中嵌入 Checkpoint 调用 */
void Runnable_ESP_Control(void) {
    WdgM_CheckpointReached(SE_ESP, CP_Init);

    ESP_ReadSensors();
    WdgM_CheckpointReached(SE_ESP, CP_SensorRead);

    ESP_RunAlgorithm();
    WdgM_CheckpointReached(SE_ESP, CP_Algorithm);

    if (safety_check_passed()) {
        ESP_ApplyActuator();
        WdgM_CheckpointReached(SE_ESP, CP_ActuatorCmd);
    } else {
        ESP_EnterSafeState();
        WdgM_CheckpointReached(SE_ESP, CP_SafeState);
    }

    WdgM_CheckpointReached(SE_ESP, CP_Done);
}
```

**安全关断路径 (Safe Shutdown Path)**：

```
触发源                                   响应
─────────                               ─────
WdgM Global Status = EXPIRED  ──┐
MPU Violation (ProtectionHook) ──┤
HW Diag: Voltage Out of Range ──┼──→ Safe State Manager
Stack Overflow Detected ─────────┤         │
E2E Check: WRONG_SEQUENCE ──────┘         ▼
                                    ┌─────────────────┐
                                    │ 1. 切断执行器输出 │
                                    │ 2. 通知其他 ECU  │
                                    │    (via CAN/ETH) │
                                    │ 3. 记录 DTC      │
                                    │ 4. 停止喂狗       │
                                    │    → HW Reset     │
                                    └─────────────────┘
```

#### 5.1.4 MCAL 硬件诊断与软件诊断交互

| 硬件诊断机制 | MCAL 模块 | 软件响应 |
|-------------|----------|---------|
| **ECC (Error Correcting Code)** | Mcu Driver → NMI | 单比特纠正 (SBE): 记录 DTC，继续运行；双比特错误 (DBE): 触发安全关断 |
| **Lockstep Core 比较** | HW Diag → NMI | 比较失败触发立即复位，Dem 在上次复位后记录事件 |
| **BIST (Built-in Self Test)** | EcuM Startup | 启动阶段执行 CPU/RAM BIST，失败则禁止进入 RUN 状态 |
| **Voltage Monitor** | Mcu Driver → IRQ | 超出安全阈值 → Dem_ReportError → WdgM 降级 |
| **Clock Monitor** | Mcu Driver → IRQ | PLL 失锁 → 切换到备用时钟 → 记录 DTC |
| **Temperature** | Adc Driver → 周期采样 | 过温 → 降频/降级，临界 → 安全关断 |

#### 5.1.5 时间保护与 WdgM 分层监控

时间保护的三级监控体系：

| 级别 | 机制 | 检测对象 | 响应时间 |
|-----|------|---------|---------|
| **L1: OS 时间保护** | 硬件定时器 + ProtectionHook | 单个 Task/ISR 超时 | < 100μs |
| **L2: WdgM 软件监控** | Alive/Deadline/Logical | Supervised Entity 异常 | 1 ~ N 个周期 |
| **L3: 硬件看门狗** | External WDT (Window) | 系统级挂死 | 看门狗超时周期 (通常 10-100ms) |

### 5.2 信息安全 (ISO 21434)

#### 5.2.1 安全启动链 (Secure Boot)

```
┌────────────────────────────────────────────────────────────────────┐
│                        Secure Boot Chain                            │
│                                                                      │
│  ┌──────────┐  verify  ┌──────────────┐  verify  ┌──────────────┐  │
│  │ ROM Boot │ ───────→ │  1st Stage   │ ───────→ │  2nd Stage   │  │
│  │ (HW RoT) │  (HSM)   │  Bootloader  │  (HSM)   │  Bootloader  │  │
│  │ (不可变)  │          │  (SPL/U-Boot)│          │  (NuttX BL)  │  │
│  └──────────┘          └──────────────┘          └──────┬───────┘  │
│                                                          │ verify   │
│                                                          ▼ (HSM)   │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                NuttX Kernel + AUTOSAR BSW Image               │  │
│  │  RSA-2048/ECDSA-P256 签名 | SHA-256 Hash | Anti-Rollback     │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              │ verify                               │
│                              ▼ (HSM)                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    SWC Application Image                       │  │
│  │  独立签名验证 | 版本号检查 | 完整性校验                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

**NuttX 引导过程集成**：

```c
int nuttx_secure_boot(void) {
    /* 1. HSM 验证 NuttX 内核镜像签名 */
    if (hsm_verify_image(NUTTX_IMAGE_ADDR, NUTTX_IMAGE_SIZE,
                         NUTTX_IMAGE_SIG, HSM_KEY_SLOT_BOOT) != HSM_OK) {
        /* 签名验证失败，进入恢复模式 */
        enter_recovery_mode();
        return -1;
    }

    /* 2. Anti-Rollback: 检查版本号 */
    uint32_t current_ver = get_image_version(NUTTX_IMAGE_ADDR);
    uint32_t min_ver = hsm_read_monotonic_counter(HSM_COUNTER_FW_VERSION);
    if (current_ver < min_ver) {
        enter_recovery_mode();
        return -1;
    }

    /* 3. 更新单调计数器 */
    hsm_increment_monotonic_counter(HSM_COUNTER_FW_VERSION, current_ver);

    /* 4. 启动 NuttX */
    jump_to_nuttx(NUTTX_IMAGE_ADDR);
    return 0;
}
```

#### 5.2.2 SecOC 在 PDU 路由中的集成

SecOC (Secure Onboard Communication) 为车内通信提供消息认证：

```
发送路径:
SWC → RTE → COM → PduR → SecOC (MAC 计算 + Freshness 附加) → PduR → CanIf/EthIf

接收路径:
CanIf/EthIf → PduR → SecOC (MAC 校验 + Freshness 验证) → PduR → COM → RTE → SWC
```

**新鲜度值 (Freshness Value) 管理方案**：

| 方案 | 说明 | 适用场景 |
|-----|------|---------|
| **基于计数器 (Trip Counter)** | 每次发送递增，接收端维护同步窗口 | CAN/CAN FD (带宽受限) |
| **基于时间戳** | 使用全局同步时钟 (StbM) 生成 | 以太网 (带宽充裕) |
| **截断新鲜度值 (Truncated FV)** | 仅传输低 N 位，接收端重建完整值 | CAN (节省帧空间) |

```c
/* SecOC 新鲜度管理器接口 */
Std_ReturnType FvM_GetTxFreshness(
    uint16_t SecOCFreshnessValueID,
    uint8_t *FreshnessValue,
    uint32_t *FreshnessValueLength)
{
    FvM_CounterType *counter = &g_fvm_tx_counters[SecOCFreshnessValueID];

    counter->value++;
    memcpy(FreshnessValue, &counter->value, sizeof(counter->value));
    *FreshnessValueLength = counter->bit_length;

    return E_OK;
}

Std_ReturnType FvM_GetRxFreshness(
    uint16_t SecOCFreshnessValueID,
    const uint8_t *TruncatedFreshnessValue,
    uint32_t TruncatedFVLength,
    uint8_t *FreshnessValue,
    uint32_t *FreshnessValueLength)
{
    FvM_CounterType *counter = &g_fvm_rx_counters[SecOCFreshnessValueID];

    /* 使用截断值重建完整新鲜度值 */
    uint64_t reconstructed = reconstruct_freshness(
        counter->value, TruncatedFreshnessValue, TruncatedFVLength);

    /* 验证新鲜度 (防重放) */
    if (reconstructed <= counter->value) {
        return E_NOT_OK;
    }

    counter->value = reconstructed;
    memcpy(FreshnessValue, &reconstructed, sizeof(reconstructed));
    *FreshnessValueLength = counter->bit_length;

    return E_OK;
}
```

#### 5.2.3 Crypto 服务栈与 HSM 硬件加速

```
┌──────────────────────────────────────────────────────┐
│                Crypto Service Stack                    │
│                                                        │
│  ┌─────────────┐                                      │
│  │    Csm      │  Job-based Async/Sync API            │
│  │             │  AES, SHA, RSA, ECDSA, CMAC...       │
│  └──────┬──────┘                                      │
│         │ CryIf_ProcessJob()                          │
│  ┌──────▼──────┐                                      │
│  │   CryIf     │  Routing: Job → Crypto Driver        │
│  │             │  Multi-driver abstraction             │
│  └──────┬──────┘                                      │
│    ┌────┴──────────────┐                              │
│    │                   │                              │
│  ┌─▼─────────┐  ┌─────▼─────────┐                    │
│  │ Crypto SW  │  │ Crypto HW    │                    │
│  │ Driver     │  │ Driver (HSM) │                    │
│  │ (mbedTLS)  │  │ (Mailbox API)│                    │
│  └────────────┘  └──────┬───────┘                    │
│                         │                             │
│                  ┌──────▼───────┐                     │
│                  │   HSM HW     │                     │
│                  │ Key Storage  │                     │
│                  │ AES Engine   │                     │
│                  │ PKA Engine   │                     │
│                  └──────────────┘                     │
└──────────────────────────────────────────────────────┘
```

- **Csm** 提供统一的加密服务 API，上层模块 (SecOC, TLS, DDS-Security) 通过 `Csm_Encrypt`, `Csm_MacGenerate`, `Csm_SignatureVerify` 等接口使用。
- **CryIf** 根据 Job 配置将请求路由到软件实现 (mbedTLS) 或硬件加速器 (HSM)。
- **HSM 驱动**：通过共享内存 Mailbox 与 HSM 固件通信，NuttX 端实现为 CDD 字符设备 `/dev/hsm0`。

#### 5.2.4 DDS 安全特性 (DDS-Security)

DDS-Security 是 OMG 标准定义的安全插件体系，包含：

| 插件 | 功能 | 实现 |
|-----|------|-----|
| **Authentication** | 参与者身份认证 (PKI/Certificate) | X.509 证书 + ECDSA 握手 |
| **Access Control** | 基于策略的 Topic/Domain 访问控制 | Governance + Permissions XML |
| **Cryptographic** | 消息加密 + 签名 (AES-GCM-256) | 调用 AUTOSAR Csm 接口 |

**DDS-Security 与 AUTOSAR Crypto 栈的集成**：

```c
/* DDS-Security Crypto Plugin 桥接到 AUTOSAR Csm */
typedef struct {
    dds_security_crypto_plugin_t base;
    Csm_JobType                 aes_gcm_job;
    Csm_KeyType                 session_key;
} AutosarCryptoPlugin;

int autosar_dds_encrypt(void *plugin, const uint8_t *plain,
                        size_t plain_len, uint8_t *cipher,
                        size_t *cipher_len)
{
    AutosarCryptoPlugin *p = (AutosarCryptoPlugin *)plugin;

    Csm_Encrypt(p->aes_gcm_job.jobId, CRYPTO_OPERATIONMODE_SINGLECALL,
                plain, plain_len, cipher, cipher_len);

    return DDS_SECURITY_OK;
}
```

**Access Control 配置示例**：

```xml
<!-- DDS Governance (domain_access_rules.xml) -->
<domain_access_rules>
  <domain_rule>
    <domains><id>0</id></domains>
    <allow_unauthenticated_participants>false</allow_unauthenticated_participants>
    <enable_join_access_control>true</enable_join_access_control>
    <topic_access_rules>
      <topic_rule>
        <topic_expression>Vehicle/Chassis/*</topic_expression>
        <enable_read_access_control>true</enable_read_access_control>
        <enable_write_access_control>true</enable_write_access_control>
        <data_protection_kind>ENCRYPT</data_protection_kind>
      </topic_rule>
    </topic_access_rules>
  </domain_rule>
</domain_access_rules>
```

#### 5.2.5 诊断安全访问与网络隔离

**UDS 安全访问 (0x27 / 0x29)**：

- **Service 0x27 (SecurityAccess)**：传统 Seed-Key 挑战响应机制，使用 HSM 生成随机 Seed 和验证 Key。
- **Service 0x29 (Authentication)**：R22-11 新增的 PKI 证书认证，支持单向/双向认证，流程：

```
Tester                          ECU (NuttX)
  │                                │
  │── 0x29 01 (deAuthenticate) ──→│
  │←── 0x69 01 (positive) ────────│
  │                                │
  │── 0x29 02 (verifyCertUnidi) ──→│  HSM 验证 Tester 证书
  │    + Tester Certificate        │
  │←── 0x69 02 (challenge) ────────│  返回 Challenge
  │                                │
  │── 0x29 03 (verifyProofOfOwn) ─→│  HSM 验证签名
  │    + Signed Challenge          │
  │←── 0x69 03 (positive) ────────│  认证成功
  │                                │
  │── 0x2E / 0x31 (受保护服务) ──→│  允许访问
```

**网络隔离/防火墙**：

```
┌──────────────────────────────────────────────────────────────┐
│              Ethernet Firewall (BSW Service Layer)             │
│                                                                │
│  ┌────────────────────────────────────────────────────────┐   │
│  │  ACL Engine (Access Control List)                       │   │
│  │  ┌─────────────────────────────────────────────────┐   │   │
│  │  │ Rule 1: ALLOW 192.168.1.0/24 → DoIP (Port 13400)│   │   │
│  │  │ Rule 2: ALLOW 239.x.x.x → SOME/IP-SD (30490)   │   │   │
│  │  │ Rule 3: ALLOW DDS_Domain_0 → UDP 7400-7500      │   │   │
│  │  │ Rule 4: DENY  * → * (Default Deny)              │   │   │
│  │  └─────────────────────────────────────────────────┘   │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │ VLAN Filter  │  │ Rate Limiter │  │ Anomaly Detector │    │
│  │ VLAN 10: OBD │  │ Max 1Mbps   │  │ IdsM Integration │    │
│  │ VLAN 20: V2X │  │ per source  │  │ DPI (Deep Packet)│    │
│  │ VLAN 30: Int │  │             │  │                  │    │
│  └──────────────┘  └──────────────┘  └──────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

NuttX 层面通过 `CONFIG_NET_ETHERNET_VLAN=y` 支持 VLAN，防火墙 ACL 在 `EthIf` 层以 Rx/Tx Hook 形式注入：

```c
int ethif_firewall_rx_hook(FAR struct net_driver_s *dev,
                           FAR uint8_t *frame, size_t len) {
    EthFirewall_PacketInfo pkt;
    ethfw_parse_packet(frame, len, &pkt);

    if (ethfw_check_acl(&pkt) == ETHFW_DENY) {
        IdsM_ReportSecurityEvent(IDSM_EVT_FIREWALL_BLOCK, &pkt);
        return -EACCES;
    }

    if (ethfw_check_rate_limit(&pkt) == ETHFW_RATE_EXCEEDED) {
        IdsM_ReportSecurityEvent(IDSM_EVT_RATE_LIMIT, &pkt);
        return -EBUSY;
    }

    return OK;
}
```

#### 5.2.6 安全日志与安全事件管理

**IdsM (Intrusion Detection System Manager)** 收集安全事件并持久化存储：

```c
typedef struct {
    uint32_t    timestamp;
    uint16_t    event_id;
    uint8_t     severity;     /* IDSM_SEV_INFO / WARNING / CRITICAL */
    uint8_t     source_module;
    uint32_t    source_addr;
    uint16_t    detail_length;
    uint8_t     detail_data[IDSM_MAX_DETAIL_SIZE];
} IdsM_SecurityEvent;

/* 安全事件类型 */
#define IDSM_EVT_SECOC_MAC_FAIL       0x0001
#define IDSM_EVT_SECOC_FRESHNESS_FAIL 0x0002
#define IDSM_EVT_FIREWALL_BLOCK       0x0010
#define IDSM_EVT_RATE_LIMIT           0x0011
#define IDSM_EVT_DDS_AUTH_FAIL        0x0020
#define IDSM_EVT_DDS_ACCESS_DENY      0x0021
#define IDSM_EVT_DIAG_AUTH_FAIL       0x0030
#define IDSM_EVT_SECURE_BOOT_FAIL     0x0040
#define IDSM_EVT_KEY_COMPROMISE       0x0050
```

- 安全日志通过 NvM 持久化存储，使用 Redundant Block 防止篡改。
- 日志可通过 DoIP/DDS 上报到云端安全运营中心 (SOC)。
- 日志区域受 MPU 保护，仅 IdsM 模块有写权限。

---

## 6. 开发与集成建议

### 6.1 AUTOSAR 配置工具与 NuttX 适配

#### 6.1.1 工具链选型

| 工具 | 用途 | NuttX 适配要点 |
|-----|------|---------------|
| **Vector DaVinci Developer** | SWC 建模、Port 定义、Runnable 规划 | 标准使用，无需特殊适配 |
| **Vector DaVinci Configurator Pro** | BSW 模块参数配置 | OS 配置生成 AUTOSAR OS 参数，由 Shim 层翻译为 NuttX 配置 |
| **EB tresos Studio** | 替代 DaVinci 的 BSW 配置工具 | 同上 |
| **AUTOSAR RTE Generator** | 根据 SWC 描述生成 RTE 代码 | 生成的 RTE 代码中 OS API 调用由 Shim 层拦截 |

#### 6.1.2 配置生成流程

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Configuration & Code Generation Flow               │
│                                                                        │
│  ┌────────────┐     ┌──────────────┐     ┌────────────────────────┐  │
│  │ ARXML      │     │ DaVinci /    │     │ Generated Code          │  │
│  │ (SWC Desc) │────→│ EB tresos    │────→│ ├── Rte.c / Rte.h      │  │
│  │ (BSW Cfg)  │     │              │     │ ├── Com_Cfg.c           │  │
│  │ (ECU Ext)  │     │              │     │ ├── Os_Cfg.h            │  │
│  └────────────┘     └──────────────┘     │ ├── SecOC_Cfg.c         │  │
│                                           │ ├── WdgM_Cfg.c          │  │
│                                           │ └── ...                  │  │
│                                           └───────────┬──────────────┘  │
│                                                       │                 │
│  ┌────────────────────────────────────────────────────▼──────────────┐  │
│  │                 NuttX Adaptation Post-Processing                   │  │
│  │                                                                    │  │
│  │  1. Os_Cfg.h → nuttx_os_shim_cfg.h (Task→pthread 映射表)         │  │
│  │  2. 生成 Kconfig 片段 (CONFIG_AUTOSAR_xxx=y)                      │  │
│  │  3. 生成 MPU Region Table (基于 OS-Application 配置)              │  │
│  │  4. 生成 NuttX defconfig (合并 AUTOSAR 所需 Kconfig 选项)         │  │
│  │  5. DDS IDL → C 结构体 (与 AUTOSAR S/R Port 对齐)                │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

**Os_Cfg.h → NuttX 适配转换示例**：

```python
# post_process_os_cfg.py
# 将 AUTOSAR OS 配置转换为 NuttX 线程配置

import xml.etree.ElementTree as ET

def convert_os_cfg(arxml_path, output_path):
    tree = ET.parse(arxml_path)
    tasks = tree.findall('.//OsTask')

    with open(output_path, 'w') as f:
        f.write('/* Auto-generated NuttX OS Shim Configuration */\n\n')
        for task in tasks:
            name = task.find('SHORT-NAME').text
            prio = int(task.find('OsTaskPriority').text)
            stack = int(task.find('OsTaskStackSize').text)
            f.write(f'static const OsTaskShimCfg g_task_{name} = {{\n')
            f.write(f'    .name       = "{name}",\n')
            f.write(f'    .nuttx_prio = {prio},\n')
            f.write(f'    .stack_size = {stack},\n')
            f.write(f'    .sched_policy = SCHED_FIFO,\n')
            f.write(f'}};\n\n')
```

### 6.2 DDS 配置与代码生成工具

#### 6.2.1 DDS IDL 定义与代码生成

```idl
// vehicle_types.idl
module Vehicle {
    module Chassis {
        @topic
        struct WheelSpeed {
            @key uint8 wheel_id;    // FL=0, FR=1, RL=2, RR=3
            float speed_mps;        // m/s
            uint64 timestamp_ns;    // nanoseconds since boot
            uint8 quality;          // signal quality indicator
        };

        @topic
        struct VehicleDynamics {
            float yaw_rate;         // rad/s
            float lateral_accel;    // m/s^2
            float longitudinal_accel;
            uint64 timestamp_ns;
        };
    };
};
```

**代码生成工具集成**：

```bash
# 使用 Fast DDS Gen 生成序列化代码
fastddsgen -d generated/ -typeros2 vehicle_types.idl

# 或使用 Cyclone DDS idlc
idlc -l c vehicle_types.idl -o generated/

# 生成的文件:
# generated/vehicle_types.h       - 类型定义
# generated/vehicle_types.c       - 序列化/反序列化
# generated/vehicle_typesPlugin.c - DDS Type Support
```

#### 6.2.2 DDS QoS Profile 配置

```xml
<!-- dds_qos_profiles.xml -->
<dds xmlns="http://www.eprosima.com/XMLSchemas/fastRTPS_Profiles">
  <profiles>
    <data_writer profile_name="ChassisReliable10ms">
      <qos>
        <reliability><kind>RELIABLE</kind></reliability>
        <deadline><period><nanosec>10000000</nanosec></period></deadline>
        <liveliness>
          <kind>AUTOMATIC</kind>
          <lease_duration><nanosec>50000000</nanosec></lease_duration>
        </liveliness>
        <history><kind>KEEP_LAST</kind><depth>1</depth></history>
      </qos>
    </data_writer>

    <data_writer profile_name="SensorBestEffort">
      <qos>
        <reliability><kind>BEST_EFFORT</kind></reliability>
        <history><kind>KEEP_LAST</kind><depth>5</depth></history>
        <resource_limits>
          <max_samples>10</max_samples>
          <max_instances>4</max_instances>
        </resource_limits>
      </qos>
    </data_writer>
  </profiles>
</dds>
```

### 6.3 构建系统

#### 6.3.1 推荐方案: CMake 统一构建

NuttX 从 12.x 起增强了 CMake 支持，建议整体迁移到 CMake 以统一管理 NuttX 内核、AUTOSAR BSW、DDS 中间件和 SWC：

```
workspace/
├── CMakeLists.txt              # 顶层 CMake
├── nuttx/                      # NuttX 源码 (submodule)
│   ├── CMakeLists.txt
│   └── ...
├── autosar_bsw/                # AUTOSAR BSW 模块
│   ├── CMakeLists.txt
│   ├── Com/
│   ├── PduR/
│   ├── SecOC/
│   ├── Dcm/
│   ├── WdgM/
│   ├── Os_Shim/               # NuttX OS 适配层
│   └── DdsSomeipBridge/       # DDS-SOME/IP 桥接
├── dds/                        # DDS 中间件
│   ├── CMakeLists.txt
│   ├── cyclonedds/            # Cyclone DDS (submodule)
│   └── idl/                   # IDL 定义
│       └── vehicle_types.idl
├── swc/                        # 应用层 SWC
│   ├── CMakeLists.txt
│   ├── Chassis_SWC/
│   ├── Body_SWC/
│   └── SafetyMonitor_SWC/
├── config/                     # 配置文件
│   ├── autosar/               # ARXML + 生成的 Cfg
│   ├── dds/                   # DDS QoS Profiles
│   └── boards/                # NuttX board config
│       ├── ccu_defconfig
│       └── zc_defconfig
├── tools/                      # 构建辅助工具
│   ├── post_process_os_cfg.py
│   └── gen_mpu_table.py
└── test/                       # 测试
    ├── sil/
    └── hil/
```

**顶层 CMakeLists.txt**：

```cmake
cmake_minimum_required(VERSION 3.20)
project(VehicleOS C CXX ASM)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)

# NuttX 内核
set(NUTTX_BOARD "custom_board")
set(NUTTX_CONFIG "ccu")
add_subdirectory(nuttx)

# AUTOSAR BSW
add_subdirectory(autosar_bsw)

# DDS 中间件
set(BUILD_SHARED_LIBS OFF)
set(CYCLONEDDS_ENABLE_SECURITY ON)
add_subdirectory(dds)

# DDS IDL 代码生成
find_program(IDLC idlc REQUIRED)
add_custom_command(
    OUTPUT ${CMAKE_BINARY_DIR}/generated/vehicle_types.h
           ${CMAKE_BINARY_DIR}/generated/vehicle_types.c
    COMMAND ${IDLC} -l c ${CMAKE_SOURCE_DIR}/dds/idl/vehicle_types.idl
            -o ${CMAKE_BINARY_DIR}/generated/
    DEPENDS dds/idl/vehicle_types.idl
)

# SWC 应用
add_subdirectory(swc)

# 链接
target_link_libraries(vehicle_os
    nuttx_kernel
    autosar_bsw
    cyclonedds::ddsc
    swc_all
)
```

#### 6.3.2 Kconfig 与 AUTOSAR 配置的对齐

```kconfig
# autosar_bsw/Kconfig
menu "AUTOSAR BSW Configuration"

config AUTOSAR_BSW_ENABLE
    bool "Enable AUTOSAR BSW"
    default y

config AUTOSAR_COM_ENABLE
    bool "Enable COM module"
    default y
    depends on AUTOSAR_BSW_ENABLE

config AUTOSAR_SECOC_ENABLE
    bool "Enable SecOC module"
    default y
    depends on AUTOSAR_COM_ENABLE

config AUTOSAR_DDS_BRIDGE_ENABLE
    bool "Enable DDS-SOME/IP Bridge"
    default y
    depends on AUTOSAR_COM_ENABLE

config AUTOSAR_DDS_SECURITY_ENABLE
    bool "Enable DDS-Security Plugin"
    default y
    depends on AUTOSAR_DDS_BRIDGE_ENABLE && CRYPTO_MBEDTLS

config AUTOSAR_WDGM_ENABLE
    bool "Enable WdgM (Watchdog Manager)"
    default y
    depends on AUTOSAR_BSW_ENABLE && WATCHDOG

endmenu
```

### 6.4 测试方案

#### 6.4.1 SIL (Software-in-the-Loop) 测试

```
┌──────────────────────────────────────────────────────────────┐
│                    SIL Test Environment                        │
│                                                                │
│  ┌──────────────────┐     ┌────────────────────────────────┐  │
│  │  Host PC (Linux) │     │  QEMU / NuttX Sim             │  │
│  │                  │     │  ┌──────────────────────────┐  │  │
│  │  ┌────────────┐  │     │  │  NuttX + AUTOSAR BSW     │  │  │
│  │  │ Test Runner│  │     │  │  + DDS + SWC             │  │  │
│  │  │ (pytest)   │──┼─────┼─→│                          │  │  │
│  │  └────────────┘  │     │  └──────────────────────────┘  │  │
│  │                  │     │                                │  │
│  │  ┌────────────┐  │     │  ┌──────────────────────────┐  │  │
│  │  │ vCAN /     │  │     │  │  Virtual CAN / ETH       │  │  │
│  │  │ vETH       │──┼─────┼─→│  (SocketCAN + TAP)       │  │  │
│  │  └────────────┘  │     │  └──────────────────────────┘  │  │
│  │                  │     │                                │  │
│  │  ┌────────────┐  │     │  ┌──────────────────────────┐  │  │
│  │  │ DDS Peer   │  │     │  │  DDS (Cyclone DDS)       │  │  │
│  │  │ (Spy/Rec)  │──┼─────┼─→│  Domain Participant      │  │  │
│  │  └────────────┘  │     │  └──────────────────────────┘  │  │
│  └──────────────────┘     └────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

- **NuttX Simulator (sim)**: NuttX 提供 Linux 模拟器 (`CONFIG_ARCH_SIM=y`)，可在 Host PC 上直接运行整个协议栈。
- **虚拟 CAN**: 使用 Linux SocketCAN + `vcan` 接口模拟 CAN 总线。
- **虚拟以太网**: 使用 TAP 设备模拟以太网通信。
- **DDS 仿真**: Host 端运行 DDS Subscriber/Publisher 对端，验证 Topic 收发、QoS 行为和安全认证。

**DDS SIL 测试脚本示例**：

```python
# test_dds_wheel_speed.py
import cyclonedds.core as dds
import cyclonedds.domain as domain
import cyclonedds.topic as topic
import cyclonedds.sub as sub
import time

@dds.dataclass
class WheelSpeed:
    wheel_id: int = 0
    speed_mps: float = 0.0
    timestamp_ns: int = 0
    quality: int = 0

def test_wheel_speed_reception():
    participant = domain.DomainParticipant(domain_id=0)
    tp = topic.Topic(participant, "Vehicle/Chassis/WheelSpeed", WheelSpeed)
    reader = sub.DataReader(tp)

    samples = []
    deadline = time.time() + 5.0
    while time.time() < deadline and len(samples) < 4:
        for sample in reader.take(N=10):
            samples.append(sample)

    assert len(samples) >= 4, f"Expected 4 wheel samples, got {len(samples)}"
    wheel_ids = {s.wheel_id for s in samples}
    assert wheel_ids == {0, 1, 2, 3}, f"Missing wheels: {wheel_ids}"
```

#### 6.4.2 HIL (Hardware-in-the-Loop) 测试

| 测试维度 | 工具/接口 | 测试内容 |
|---------|----------|---------|
| **CAN 通信** | Vector CANoe / PCAN | PDU 收发、E2E 校验、SecOC MAC 验证 |
| **以太网通信** | Wireshark + Ethernet TAP | SOME/IP SD、DoIP、DDS RTPS 报文分析 |
| **DDS 特性** | DDS Spy (eProsima) | Topic 发现、QoS 策略验证、DDS-Security 握手 |
| **诊断** | CANoe DiVa / ODXStudio | UDS 服务全量测试、安全访问认证 |
| **功能安全** | Fault Injection Tool | MPU 违例注入、WdgM 超时模拟、E2E 错误注入 |
| **信息安全** | Pentest Framework | SecOC 重放攻击、DDS 未授权访问、防火墙绕过 |

### 6.5 从单域控制器到整车中央计算的演进路线

```
Phase 1: 单域 ECU (当前)
━━━━━━━━━━━━━━━━━━━━
• NuttX + AUTOSAR BSW on Cortex-M7/R5
• CAN/CAN FD 为主, 单一功能域
• 功能安全: ASIL-B, 单核
• 无 DDS, SOME/IP 有限使用

         ↓ 迭代

Phase 2: 区域控制器 (ZC)
━━━━━━━━━━━━━━━━━━━━━━━━
• NuttX SMP on Cortex-R52 双核
• CAN FD + 100BASE-T1 以太网
• 整合 2-3 个域, SOME/IP 网关
• DDS: Micro-XRCE-DDS Client
• 功能安全: ASIL-D (Lockstep)
• SecOC 全量部署

         ↓ 迭代

Phase 3: 中央计算单元 (CCU)
━━━━━━━━━━━━━━━━━━━━━━━━━━━
• NuttX (Safety Island) + Linux (App Core)
• Jailhouse AMP 隔离
• 1000BASE-T1 以太网 + TSN
• DDS: Cyclone DDS (完整 RTPS)
• DDS ↔ SOME/IP 桥接
• DDS-Security 全量部署
• 全域融合, OTA 支持

         ↓ 迭代

Phase 4: 整车操作系统平台化
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• 统一 SDK + 标准化 API
• SWC 跨 ECU 动态部署 (DDS Topic 自动路由)
• 云端安全运维 (IdsM → Cloud SOC)
• CI/CD + OTA A/B 分区更新
• 车路云一体化 (V2X via DDS)
```

**关键技术节点**：

| 阶段 | 关键技术挑战 | 建议投入 |
|-----|------------|---------|
| **Phase 1→2** | NuttX SMP 稳定性验证、SOME/IP 栈在 NuttX 上的移植 | MCAL 开发、OS Shim 层开发 |
| **Phase 2→3** | Jailhouse + OpenAMP 核间通信、DDS 完整栈移植、DDS-Security 与 HSM 集成 | 跨核架构设计、安全认证准备 |
| **Phase 3→4** | 动态 SWC 部署框架、云端一体化运维、V2X 协议集成 | 平台化 SDK 开发、生态建设 |

### 6.6 关键风险与缓解措施

| 风险 | 影响 | 缓解措施 |
|-----|------|---------|
| NuttX 未通过 ISO 26262 认证 | 无法直接用于 ASIL-D 产品 | 1) 通过 QM + Safety Manual 路径; 2) 关键路径使用经过认证的 SafeRTOS 替代; 3) 申请第三方评估 |
| AUTOSAR BSW 源码许可 | 商业 BSW 模块需要授权 | 1) 选择 Vector/EB 的商业方案; 2) 关键模块自研 (参考 AUTOSAR 规范实现); 3) 开源替代 (如 Arctic Core 的部分模块) |
| DDS 在嵌入式平台的内存开销 | 资源受限 ZC 上可能超出 RAM 预算 | 1) ZC 使用 Micro-XRCE-DDS (极低资源占用); 2) CCU 使用完整 DDS; 3) 按需裁剪 DDS 特性 |
| NuttX 网络栈性能 | 高带宽以太网场景可能不足 | 1) 启用 DMA Zero-Copy; 2) 使用 NuttX 的 IOB (I/O Buffer) 优化; 3) 关键路径使用 XDP/DPDK 类技术 |
| 多工具链集成复杂度 | AUTOSAR 配置工具 + DDS 代码生成 + NuttX 构建系统 | 1) CMake 统一构建; 2) CI/CD 自动化流水线; 3) 专用 Post-Processing 脚本 |

---

> **本文档为架构设计参考，具体实施时需根据目标硬件平台、AUTOSAR 供应商选型和产品安全等级进行详细适配。**
