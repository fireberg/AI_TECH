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

### 2.1 Classic AUTOSAR 分层模型

本架构图严格参照 **AUTOSAR Classic Platform Layered Architecture (R22-11)** 标准绘制，采用 Classic 规范中定义的自下而上六层结构，并在两侧补充 OS 栏与通信栈栏：

| 层次 (Classic AUTOSAR) | 英文名称 | 本方案内容 |
|------------------------|----------|-----------|
| **L1** | Microcontroller | MCU/SoC、CAN/Ethernet/LIN、Flash、HSM、WDT、MPU 等硬件 |
| **L2** | Microcontroller Abstraction Layer (MCAL) | Can、Lin、Eth、Spi、Dio、Adc、Pwm、Gpt、Fls、Wdg 等标准 MCAL 驱动 |
| **L3** | ECU Abstraction Layer | Communication HW Abstraction (CanIf/EthIf/SoAd 等)、Memory HW Abstraction (Fee/Ea)、I/O HW Abstraction (IoHwAb)、Complex Device Drivers (CDD) |
| **L4** | Services Layer | Communication / Memory / Diagnostic / Crypto / Off-board / System Services |
| **L5** | Runtime Environment (RTE) | S/R、C/S 通信、E2E Transformer、SecOC 注入、DDS-RTE Bridge |
| **L6** | Application Layer | 各功能域 SWC (Software Component) |

**Classic 架构附加栏位**：

- **左侧 OS 栏**：AUTOSAR OS API (NuttX Adapter) + NuttX Kernel，贯穿 BSW 各层，提供 Task/ISR/Resource/Alarm/Schedule Table 及 MPU 时间保护。
- **右侧通信栈栏**：Classic AUTOSAR 标准 PDU 数据流路径 `Com → PduR → CanTp/SoAd → CanIf/EthIf → MCAL`，并扩展 SOME/IP、DDS 及 DDS-Security 分支。

**设计原则**：

1. **Classic 分层合规**：BSW 模块归属严格按 R22-11 规范划分至 Services Layer 或 ECU Abstraction Layer，不跨层调用。
2. **NuttX 作为 OS 实现**：通过 AUTOSAR OS API Shim 适配 NuttX，NuttX 网络栈映射为 TcpIp 模块，文件系统映射为 Fee/NvM 底层。
3. **跨域融合**：CCU + ZC 集中式 E/E 架构，多域 SWC 通过 RTE VFB (Virtual Function Bus) 和 DDS Topic 互联。
4. **安全贯穿**：功能安全 (ISO 26262) 与信息安全 (ISO 21434) 模块在 Classic 各层标注 `[FuSa]` / `[CySec]`。
5. **DDS 扩展集成**：DDS 作为 Communication Services 层扩展中间件，通过 Bridge 与 Classic PDU 路由及 SOME/IP 共存。

### 2.2 分层图颜色约定

| 颜色 | 含义 |
|------|------|
| 🟢 **绿色泳道** (`#E8F5E9`) | Application Layer (SWC) |
| 🔵 **蓝色泳道** (`#E3F2FD`) | Runtime Environment (RTE) |
| 🟠 **橙色泳道** (`#FFF3E0`) | BSW Services Layer |
| 🟣 **紫色泳道** (`#F3E5F5`) | ECU Abstraction Layer |
| ⬜ **灰色泳道** (`#ECEFF1`) | MCAL |
| 🟠 **深橙泳道** (`#FFE0B2`) | Microcontroller (Hardware) |
| 🟡 **黄色 OS 栏** (`#FFF2CC`) | AUTOSAR OS / NuttX Kernel |
| 🔴 **红色模块** (`#FFE0E0`) | `[FuSa]` 功能安全相关 |
| 🔵 **蓝色模块** (`#E0E0FF`) | `[CySec]` 信息安全相关 |
| 🟢 **绿色模块** (`#E0FFE0`) | `[DDS]` DDS 相关 |

### 2.3 draw.io 架构分层图（mxGraph XML）

> 为避免 draw.io 把 Markdown 文字一起当 XML 解析导致错误（如“Unescaped '<'”），建议优先使用仓库中的独立文件 **`diagram-classic-autosar.xml`** 直接导入：  
> **draw.io → File → Import from → Device/Local file → 选择 `diagram-classic-autosar.xml`**。  
> 若要通过粘贴导入，则只复制本节代码块中 ` ```xml ` 与 ` ``` ` 之间的内容。

```xml
<mxfile host="app.diagrams.net" modified="2026-06-08T12:00:00.000Z" agent="Classic AUTOSAR" version="24.0.0" type="device">
  <diagram id="classic-autosar-nuttx" name="Classic AUTOSAR Layered Architecture">
    <mxGraphModel dx="2600" dy="3200" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="0" pageScale="1" pageWidth="2800" pageHeight="2600" math="0" shadow="0">
      <root>
        <mxCell id="0"/>
        <mxCell id="1" parent="0"/>

        <!-- ========== TITLE ========== -->
        <mxCell id="title" value="&lt;b&gt;AUTOSAR Classic Platform Layered Architecture (R22-11)&lt;/b&gt;&lt;br&gt;NuttX RTOS + CCU/ZC 中央计算架构" style="text;html=1;align=center;fontSize=18;fontColor=#1A1A1A;" vertex="1" parent="1">
          <mxGeometry x="180" y="10" width="2400" height="50" as="geometry"/>
        </mxCell>

        <!-- ========== LEFT: AUTOSAR OS + NuttX (Classic vertical OS column) ========== -->
        <mxCell id="os_col_bg" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFF8E1;strokeColor=#F9A825;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="20" y="70" width="150" height="1680" as="geometry"/>
        </mxCell>
        <mxCell id="os_col_title" value="&lt;b&gt;AUTOSAR OS&lt;/b&gt;&lt;br&gt;(NuttX Adapter)" style="text;html=1;align=center;fontSize=12;fontColor=#E65100;rotation=-90;" vertex="1" parent="1">
          <mxGeometry x="35" y="200" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="os_task" value="Task&lt;br&gt;ISR Cat1/2&lt;br&gt;Resource&lt;br&gt;Event" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="35" y="90" width="120" height="70" as="geometry"/>
        </mxCell>
        <mxCell id="os_alarm" value="Alarm&lt;br&gt;Counter&lt;br&gt;Schedule Table" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="35" y="170" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="os_app" value="OS-Application&lt;br&gt;Trusted /&lt;br&gt;Non-Trusted" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="35" y="240" width="120" height="55" as="geometry"/>
        </mxCell>
        <mxCell id="os_mpu" value="&lt;b&gt;[FuSa]&lt;/b&gt;&lt;br&gt;Memory Protection&lt;br&gt;MPU/MMU&lt;br&gt;Time Protection" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="35" y="305" width="120" height="65" as="geometry"/>
        </mxCell>
        <mxCell id="os_schm" value="SchM&lt;br&gt;(BSW Scheduler)" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="35" y="380" width="120" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_title" value="&lt;b&gt;NuttX Kernel&lt;/b&gt;" style="text;html=1;align=center;fontSize=11;fontColor=#E65100;rotation=-90;" vertex="1" parent="1">
          <mxGeometry x="35" y="820" width="120" height="30" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_sched" value="Scheduler&lt;br&gt;POSIX Threads" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="35" y="440" width="120" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_irq" value="IRQ / ISR&lt;br&gt;Dispatch" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="35" y="495" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_timer" value="Timer / Tick&lt;br&gt;Tickless" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="35" y="545" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_ipc" value="Sem / Mutex&lt;br&gt;MQ / Signal" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="35" y="595" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_net" value="Network Stack&lt;br&gt;BSD Socket" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="35" y="645" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_fs" value="VFS / devfs&lt;br&gt;LittleFS / MTD" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="35" y="695" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_smp" value="SMP / AMP&lt;br&gt;OpenAMP" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="35" y="745" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="nuttx_boot" value="&lt;b&gt;[CySec]&lt;/b&gt;&lt;br&gt;Secure Boot&lt;br&gt;Chain" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="35" y="795" width="120" height="50" as="geometry"/>
        </mxCell>

        <!-- ========== LAYER 1: APPLICATION LAYER ========== -->
        <mxCell id="L_app" value="&lt;b&gt;Application Layer&lt;/b&gt; — Software Components (SWC)" style="swimlane;html=1;startSize=28;fillColor=#E8F5E9;strokeColor=#2E7D32;fontColor=#1B5E20;fontSize=13;horizontal=1;" vertex="1" parent="1">
          <mxGeometry x="180" y="70" width="2100" height="110" as="geometry"/>
        </mxCell>
        <mxCell id="swc1" value="Powertrain SWC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_app">
          <mxGeometry x="10" y="35" width="130" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="swc2" value="Chassis SWC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_app">
          <mxGeometry x="150" y="35" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="swc3" value="Body SWC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_app">
          <mxGeometry x="280" y="35" width="110" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="swc4" value="ADAS SWC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_app">
          <mxGeometry x="400" y="35" width="110" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="swc5" value="Diagnostic SWC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_app">
          <mxGeometry x="520" y="35" width="120" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="swc6" value="&lt;b&gt;[FuSa]&lt;/b&gt;&lt;br&gt;Safety Monitor SWC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=10;fontColor=#CC0000;" vertex="1" parent="L_app">
          <mxGeometry x="650" y="35" width="140" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="swc7" value="&lt;b&gt;[DDS]&lt;/b&gt;&lt;br&gt;Topic Pub/Sub SWC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=10;fontColor=#006600;" vertex="1" parent="L_app">
          <mxGeometry x="800" y="35" width="130" height="60" as="geometry"/>
        </mxCell>
        <mxCell id="swc8" value="OTA / Cloud SWC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_app">
          <mxGeometry x="940" y="35" width="120" height="60" as="geometry"/>
        </mxCell>

        <!-- ========== LAYER 2: RTE ========== -->
        <mxCell id="L_rte" value="&lt;b&gt;Runtime Environment (RTE)&lt;/b&gt;" style="swimlane;html=1;startSize=28;fillColor=#E3F2FD;strokeColor=#1565C0;fontColor=#0D47A1;fontSize=13;horizontal=1;" vertex="1" parent="1">
          <mxGeometry x="180" y="190" width="2100" height="90" as="geometry"/>
        </mxCell>
        <mxCell id="rte_sr" value="Sender-Receiver&lt;br&gt;Communication" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#1565C0;fontSize=10;" vertex="1" parent="L_rte">
          <mxGeometry x="10" y="35" width="150" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="rte_cs" value="Client-Server&lt;br&gt;Communication" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#1565C0;fontSize=10;" vertex="1" parent="L_rte">
          <mxGeometry x="170" y="35" width="150" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="rte_e2e" value="&lt;b&gt;[FuSa]&lt;/b&gt;&lt;br&gt;E2E Transformer" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=10;fontColor=#CC0000;" vertex="1" parent="L_rte">
          <mxGeometry x="330" y="35" width="130" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="rte_secoc" value="&lt;b&gt;[CySec]&lt;/b&gt;&lt;br&gt;SecOC Inject" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=10;fontColor=#0000AA;" vertex="1" parent="L_rte">
          <mxGeometry x="470" y="35" width="120" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="rte_dds" value="&lt;b&gt;[DDS]&lt;/b&gt;&lt;br&gt;DDS-RTE Bridge" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=10;fontColor=#006600;" vertex="1" parent="L_rte">
          <mxGeometry x="600" y="35" width="130" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="rte_part" value="&lt;b&gt;[FuSa]&lt;/b&gt;&lt;br&gt;OS-App Partition" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=10;fontColor=#CC0000;" vertex="1" parent="L_rte">
          <mxGeometry x="740" y="35" width="130" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="rte_vfb" value="Virtual Function Bus (VFB)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#DAEEF3;strokeColor=#0078D4;fontSize=10;dashed=1;" vertex="1" parent="L_rte">
          <mxGeometry x="880" y="35" width="200" height="45" as="geometry"/>
        </mxCell>

        <!-- ========== LAYER 3: BSW SERVICES LAYER ========== -->
        <mxCell id="L_svc" value="&lt;b&gt;Basic Software — Services Layer&lt;/b&gt;" style="swimlane;html=1;startSize=28;fillColor=#FFF3E0;strokeColor=#E65100;fontColor=#BF360C;fontSize=13;horizontal=1;" vertex="1" parent="1">
          <mxGeometry x="180" y="290" width="2100" height="380" as="geometry"/>
        </mxCell>

        <!-- Communication Services sub-lane -->
        <mxCell id="svc_comm_label" value="&lt;b&gt;Communication Services&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_svc">
          <mxGeometry x="10" y="35" width="200" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="svc_com" value="Com" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="10" y="58" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_pdur" value="PduR" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="85" y="58" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_ipdum" value="IpduM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="160" y="58" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_comm" value="ComM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="235" y="58" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_nm" value="Nm" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="310" y="58" width="60" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_someip" value="SOME/IP" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="375" y="58" width="80" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_secoc" value="&lt;b&gt;[CySec]&lt;/b&gt; SecOC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_svc">
          <mxGeometry x="460" y="58" width="90" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_e2e" value="&lt;b&gt;[FuSa]&lt;/b&gt; E2E Lib" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="L_svc">
          <mxGeometry x="555" y="58" width="90" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_dds" value="&lt;b&gt;[DDS]&lt;/b&gt; DDS Middleware" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=9;fontColor=#006600;" vertex="1" parent="L_svc">
          <mxGeometry x="650" y="58" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_dds_bridge" value="&lt;b&gt;[DDS]&lt;/b&gt; DDS-SOME/IP Bridge" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=9;fontColor=#006600;" vertex="1" parent="L_svc">
          <mxGeometry x="775" y="58" width="140" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_dds_sec" value="&lt;b&gt;[DDS+CySec]&lt;/b&gt;&lt;br&gt;DDS-Security" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#D0D0FF;strokeColor=#4400AA;fontSize=9;fontColor=#4400AA;" vertex="1" parent="L_svc">
          <mxGeometry x="920" y="58" width="110" height="35" as="geometry"/>
        </mxCell>

        <!-- Memory Services -->
        <mxCell id="svc_mem_label" value="&lt;b&gt;Memory Services&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_svc">
          <mxGeometry x="10" y="105" width="160" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="svc_nvm" value="NvM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="10" y="128" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_memif" value="MemIf" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="85" y="128" width="70" height="35" as="geometry"/>
        </mxCell>

        <!-- Diagnostic Services -->
        <mxCell id="svc_diag_label" value="&lt;b&gt;Diagnostic Services&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_svc">
          <mxGeometry x="200" y="105" width="180" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="svc_dcm" value="Dcm" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="200" y="128" width="60" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_dem" value="Dem" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="265" y="128" width="60" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_fim" value="&lt;b&gt;[FuSa]&lt;/b&gt; FiM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="L_svc">
          <mxGeometry x="330" y="128" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_det" value="Det" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="405" y="128" width="55" height="35" as="geometry"/>
        </mxCell>

        <!-- Off-board Communication -->
        <mxCell id="svc_off_label" value="&lt;b&gt;Off-board Communication&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_svc">
          <mxGeometry x="500" y="105" width="200" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="svc_doip" value="DoIP" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="500" y="128" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_diag_sec" value="&lt;b&gt;[CySec]&lt;/b&gt;&lt;br&gt;0x27/0x29 Auth" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_svc">
          <mxGeometry x="575" y="128" width="100" height="35" as="geometry"/>
        </mxCell>

        <!-- Crypto Services -->
        <mxCell id="svc_crypto_label" value="&lt;b&gt;Crypto Services&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_svc">
          <mxGeometry x="700" y="105" width="160" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="svc_csm" value="&lt;b&gt;[CySec]&lt;/b&gt; Csm" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_svc">
          <mxGeometry x="700" y="128" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_cryif" value="&lt;b&gt;[CySec]&lt;/b&gt; CryIf" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_svc">
          <mxGeometry x="775" y="128" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_keym" value="&lt;b&gt;[CySec]&lt;/b&gt; KeyM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_svc">
          <mxGeometry x="850" y="128" width="70" height="35" as="geometry"/>
        </mxCell>

        <!-- System Services -->
        <mxCell id="svc_sys_label" value="&lt;b&gt;System Services&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_svc">
          <mxGeometry x="10" y="175" width="160" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="svc_ecum" value="EcuM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="10" y="198" width="65" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_bswm" value="BswM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="80" y="198" width="65" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_wdgm" value="&lt;b&gt;[FuSa]&lt;/b&gt; WdgM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="L_svc">
          <mxGeometry x="150" y="198" width="80" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_wdgif" value="WdgIf" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="235" y="198" width="65" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_stbm" value="StbM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_svc">
          <mxGeometry x="305" y="198" width="65" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_safe" value="&lt;b&gt;[FuSa]&lt;/b&gt;&lt;br&gt;Safe State Mgr" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="L_svc">
          <mxGeometry x="375" y="198" width="100" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_ids" value="&lt;b&gt;[CySec]&lt;/b&gt; IdsM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_svc">
          <mxGeometry x="480" y="198" width="75" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="svc_fw" value="&lt;b&gt;[CySec]&lt;/b&gt;&lt;br&gt;Eth Firewall" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_svc">
          <mxGeometry x="560" y="198" width="90" height="35" as="geometry"/>
        </mxCell>

        <!-- ========== LAYER 4: ECU ABSTRACTION LAYER ========== -->
        <mxCell id="L_ecu" value="&lt;b&gt;Basic Software — ECU Abstraction Layer&lt;/b&gt;" style="swimlane;html=1;startSize=28;fillColor=#F3E5F5;strokeColor=#6A1B9A;fontColor=#4A148C;fontSize=13;horizontal=1;" vertex="1" parent="1">
          <mxGeometry x="180" y="680" width="2100" height="200" as="geometry"/>
        </mxCell>

        <!-- Communication HW Abstraction -->
        <mxCell id="ecu_comm_label" value="&lt;b&gt;Communication Hardware Abstraction&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_ecu">
          <mxGeometry x="10" y="35" width="280" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_cantp" value="CanTp" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="10" y="58" width="65" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_canif" value="CanIf" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="80" y="58" width="65" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_cantrcv" value="CanTrcv" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="150" y="58" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_linif" value="LinIf" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="225" y="58" width="60" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_lintp" value="LinTp" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="290" y="58" width="60" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_ethif" value="EthIf" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="355" y="58" width="60" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_ethtrcv" value="EthTrcv" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="420" y="58" width="70" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_soad" value="SoAd" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="495" y="58" width="60" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_tcpip" value="TcpIp&lt;br&gt;(NuttX Net)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="L_ecu">
          <mxGeometry x="560" y="58" width="80" height="35" as="geometry"/>
        </mxCell>

        <!-- Memory HW Abstraction -->
        <mxCell id="ecu_mem_label" value="&lt;b&gt;Memory Hardware Abstraction&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_ecu">
          <mxGeometry x="10" y="105" width="220" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_fee" value="Fee" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="10" y="128" width="55" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_ea" value="Ea" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="70" y="128" width="55" height="35" as="geometry"/>
        </mxCell>

        <!-- I/O HW Abstraction -->
        <mxCell id="ecu_io_label" value="&lt;b&gt;I/O Hardware Abstraction&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_ecu">
          <mxGeometry x="150" y="105" width="200" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="ecu_iohwab" value="IoHwAb" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_ecu">
          <mxGeometry x="150" y="128" width="70" height="35" as="geometry"/>
        </mxCell>

        <!-- Complex Device Drivers -->
        <mxCell id="ecu_cdd_label" value="&lt;b&gt;Complex Device Drivers (CDD)&lt;/b&gt;" style="text;html=1;align=left;fontSize=11;fontColor=#555555;" vertex="1" parent="L_ecu">
          <mxGeometry x="680" y="35" width="240" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_hsm" value="&lt;b&gt;[CySec]&lt;/b&gt;&lt;br&gt;HSM Driver" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_ecu">
          <mxGeometry x="680" y="58" width="90" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_crypto" value="&lt;b&gt;[CySec]&lt;/b&gt;&lt;br&gt;Crypto Driver" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="L_ecu">
          <mxGeometry x="775" y="58" width="90" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_dds" value="&lt;b&gt;[DDS]&lt;/b&gt;&lt;br&gt;DDS Transport" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=9;fontColor=#006600;" vertex="1" parent="L_ecu">
          <mxGeometry x="870" y="58" width="90" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_sensor" value="Sensor Fusion&lt;br&gt;CDD" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=9;" vertex="1" parent="L_ecu">
          <mxGeometry x="965" y="58" width="90" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="cdd_safe" value="&lt;b&gt;[FuSa]&lt;/b&gt;&lt;br&gt;Safety Path CDD" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="L_ecu">
          <mxGeometry x="1060" y="58" width="100" height="40" as="geometry"/>
        </mxCell>

        <!-- ========== LAYER 5: MCAL ========== -->
        <mxCell id="L_mcal" value="&lt;b&gt;Basic Software — Microcontroller Abstraction Layer (MCAL)&lt;/b&gt;" style="swimlane;html=1;startSize=28;fillColor=#ECEFF1;strokeColor=#455A64;fontColor=#263238;fontSize=13;horizontal=1;" vertex="1" parent="1">
          <mxGeometry x="180" y="890" width="2100" height="100" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_can" value="Can" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="10" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_lin" value="Lin" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="70" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_eth" value="Eth" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="130" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_spi" value="Spi" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="190" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_dio" value="Dio" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="250" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_adc" value="Adc" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="310" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_pwm" value="Pwm" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="370" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_gpt" value="Gpt" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="430" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_icu" value="Icu" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="490" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_fls" value="Fls" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="550" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_eep" value="Eep" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="610" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_mcu" value="Mcu" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="670" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_port" value="Port" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=10;" vertex="1" parent="L_mcal">
          <mxGeometry x="730" y="40" width="55" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_wdg" value="&lt;b&gt;[FuSa]&lt;/b&gt; Wdg" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="L_mcal">
          <mxGeometry x="790" y="40" width="70" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="mcal_hwdiag" value="&lt;b&gt;[FuSa]&lt;/b&gt;&lt;br&gt;HW Diag" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="L_mcal">
          <mxGeometry x="865" y="40" width="75" height="45" as="geometry"/>
        </mxCell>

        <!-- ========== LAYER 6: MICROCONTROLLER ========== -->
        <mxCell id="L_hw" value="&lt;b&gt;Microcontroller (Hardware)&lt;/b&gt;" style="swimlane;html=1;startSize=28;fillColor=#FFE0B2;strokeColor=#E65100;fontColor=#BF360C;fontSize=13;horizontal=1;" vertex="1" parent="1">
          <mxGeometry x="180" y="1000" width="2100" height="90" as="geometry"/>
        </mxCell>
        <mxCell id="hw_mcu" value="MCU/SoC&lt;br&gt;Cortex-R52/A76" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=10;" vertex="1" parent="L_hw">
          <mxGeometry x="10" y="35" width="120" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_can" value="CAN/CAN FD" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=10;" vertex="1" parent="L_hw">
          <mxGeometry x="140" y="35" width="90" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_eth" value="Ethernet PHY" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=10;" vertex="1" parent="L_hw">
          <mxGeometry x="240" y="35" width="90" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_lin" value="LIN" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=10;" vertex="1" parent="L_hw">
          <mxGeometry x="340" y="35" width="60" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_flash" value="Flash/EEPROM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=10;" vertex="1" parent="L_hw">
          <mxGeometry x="410" y="35" width="100" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_hsm" value="&lt;b&gt;[CySec]&lt;/b&gt; HSM" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#D0D0FF;strokeColor=#0000CC;fontSize=10;fontColor=#0000AA;" vertex="1" parent="L_hw">
          <mxGeometry x="520" y="35" width="90" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_wdt" value="&lt;b&gt;[FuSa]&lt;/b&gt; WDT" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFD0D0;strokeColor=#CC0000;fontSize=10;fontColor=#CC0000;" vertex="1" parent="L_hw">
          <mxGeometry x="620" y="35" width="80" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_mpu" value="&lt;b&gt;[FuSa]&lt;/b&gt; MPU" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFD0D0;strokeColor=#CC0000;fontSize=10;fontColor=#CC0000;" vertex="1" parent="L_hw">
          <mxGeometry x="710" y="35" width="80" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_switch" value="Eth Switch" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=10;" vertex="1" parent="L_hw">
          <mxGeometry x="800" y="35" width="90" height="45" as="geometry"/>
        </mxCell>
        <mxCell id="hw_sensor" value="Sensor/Actuator" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE6CC;strokeColor=#D79B00;fontSize=10;" vertex="1" parent="L_hw">
          <mxGeometry x="900" y="35" width="110" height="45" as="geometry"/>
        </mxCell>

        <!-- ========== RIGHT: Classic Communication Stack Column ========== -->
        <mxCell id="comm_col_bg" value="" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E8EAF6;strokeColor=#3949AB;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="2300" y="70" width="180" height="1020" as="geometry"/>
        </mxCell>
        <mxCell id="comm_col_title" value="&lt;b&gt;Communication Stack&lt;/b&gt;&lt;br&gt;(Classic AUTOSAR)" style="text;html=1;align=center;fontSize=11;fontColor=#283593;" vertex="1" parent="1">
          <mxGeometry x="2310" y="80" width="160" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_com" value="Com" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#3949AB;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="130" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_pdur" value="PduR" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#3949AB;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="180" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_secoc" value="&lt;b&gt;[CySec]&lt;/b&gt; SecOC" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="2330" y="230" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_e2e" value="&lt;b&gt;[FuSa]&lt;/b&gt; E2E" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="2330" y="280" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_cantp" value="CanTp" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#3949AB;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="340" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_canif" value="CanIf" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#3949AB;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="390" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_can" value="Can (MCAL)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#ECEFF1;strokeColor=#455A64;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="440" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_div1" value="── Ethernet Path ──" style="text;html=1;align=center;fontSize=9;fontColor=#666666;" vertex="1" parent="1">
          <mxGeometry x="2330" y="490" width="120" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_someip" value="SOME/IP" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#3949AB;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="515" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_soad" value="SoAd" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#3949AB;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="565" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_tcpip" value="TcpIp (NuttX)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="2330" y="615" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_ethif" value="EthIf" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#3949AB;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="665" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_eth" value="Eth (MCAL)" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#ECEFF1;strokeColor=#455A64;fontSize=10;" vertex="1" parent="1">
          <mxGeometry x="2330" y="715" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_div2" value="── DDS Path ──" style="text;html=1;align=center;fontSize=9;fontColor=#666666;" vertex="1" parent="1">
          <mxGeometry x="2330" y="765" width="120" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_dds" value="&lt;b&gt;[DDS]&lt;/b&gt; DDS Middleware" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=9;fontColor=#006600;" vertex="1" parent="1">
          <mxGeometry x="2330" y="790" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_dds_bridge" value="&lt;b&gt;[DDS]&lt;/b&gt; Bridge" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=9;fontColor=#006600;" vertex="1" parent="1">
          <mxGeometry x="2330" y="845" width="120" height="35" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_dds_sec" value="&lt;b&gt;[DDS+CySec]&lt;/b&gt;&lt;br&gt;DDS-Security" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#D0D0FF;strokeColor=#4400AA;fontSize=8;fontColor=#4400AA;" vertex="1" parent="1">
          <mxGeometry x="2330" y="895" width="120" height="40" as="geometry"/>
        </mxCell>
        <mxCell id="cstack_dds_cdd" value="&lt;b&gt;[DDS]&lt;/b&gt; CDD Transport" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=9;fontColor=#006600;" vertex="1" parent="1">
          <mxGeometry x="2330" y="950" width="120" height="35" as="geometry"/>
        </mxCell>

        <!-- ========== KEY ARROWS ========== -->
        <mxCell id="arr_app_rte" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#2E7D32;strokeWidth=+2;endArrow=classic;" edge="1" parent="1" source="L_app" target="L_rte">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_rte_svc" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#1565C0;strokeWidth=2;endArrow=classic;" edge="1" parent="1" source="L_rte" target="L_svc">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_svc_ecu" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#E65100;strokeWidth=2;endArrow=classic;" edge="1" parent="1" source="L_svc" target="L_ecu">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_ecu_mcal" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#6A1B9A;strokeWidth=2;endArrow=classic;" edge="1" parent="1" source="L_ecu" target="L_mcal">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_mcal_hw" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#455A64;strokeWidth=2;endArrow=classic;" edge="1" parent="1" source="L_mcal" target="L_hw">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_os_svc" value="OS API" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#F9A825;dashed=1;endArrow=classic;fontSize=9;" edge="1" parent="1" source="os_schm" target="L_svc">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_nuttx_mcal" value="HAL / Driver" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#D4A017;dashed=1;endArrow=classic;fontSize=9;" edge="1" parent="1" source="nuttx_fs" target="L_mcal">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_com_stack" value="Standard PDU Flow" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#3949AB;strokeWidth=2;endArrow=classic;fontSize=9;" edge="1" parent="1" source="svc_com" target="cstack_com">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_dds_bridge" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#008800;dashed=1;endArrow=classic;" edge="1" parent="1" source="svc_dds_bridge" target="cstack_dds">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_wdgm_wdg" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#CC0000;strokeWidth=2;endArrow=classic;" edge="1" parent="1" source="svc_wdgm" target="mcal_wdg">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>
        <mxCell id="arr_hsm_hw" style="edgeStyle=orthogonalEdgeStyle;rounded=0;strokeColor=#0000CC;strokeWidth=2;endArrow=classic;" edge="1" parent="1" source="cdd_hsm" target="hw_hsm">
          <mxGeometry relative="1" as="geometry"/>
        </mxCell>

        <!-- ========== LEGEND ========== -->
        <mxCell id="legend_bg" value="" style="rounded=1;whiteSpace=wrap;html=1;fillColor=#FFFFFF;strokeColor=#333333;strokeWidth=2;" vertex="1" parent="1">
          <mxGeometry x="180" y="1110" width="2300" height="80" as="geometry"/>
        </mxCell>
        <mxCell id="legend_title" value="&lt;b&gt;Legend — 图例&lt;/b&gt;" style="text;html=1;align=left;fontSize=12;" vertex="1" parent="1">
          <mxGeometry x="200" y="1118" width="120" height="20" as="geometry"/>
        </mxCell>
        <mxCell id="leg_fusa" value="[FuSa] Functional Safety" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFE0E0;strokeColor=#CC0000;fontSize=9;fontColor=#CC0000;" vertex="1" parent="1">
          <mxGeometry x="200" y="1145" width="150" height="30" as="geometry"/>
        </mxCell>
        <mxCell id="leg_cysec" value="[CySec] Cybersecurity" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0E0FF;strokeColor=#0000CC;fontSize=9;fontColor=#0000AA;" vertex="1" parent="1">
          <mxGeometry x="360" y="1145" width="150" height="30" as="geometry"/>
        </mxCell>
        <mxCell id="leg_dds" value="[DDS] Data Distribution Service" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#E0FFE0;strokeColor=#008800;fontSize=9;fontColor=#006600;" vertex="1" parent="1">
          <mxGeometry x="520" y="1145" width="180" height="30" as="geometry"/>
        </mxCell>
        <mxCell id="leg_nuttx" value="NuttX Integration" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#FFF2CC;strokeColor=#D4A017;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="710" y="1145" width="130" height="30" as="geometry"/>
        </mxCell>
        <mxCell id="leg_std" value="Standard BSW Module" style="rounded=0;whiteSpace=wrap;html=1;fillColor=#F5F5F5;strokeColor=#666666;fontSize=9;" vertex="1" parent="1">
          <mxGeometry x="850" y="1145" width="150" height="30" as="geometry"/>
        </mxCell>
        <mxCell id="leg_note" value="Layout per AUTOSAR Classic Layered Architecture (R22-11): Application → RTE → BSW Services → ECU Abstraction → MCAL → Microcontroller | OS column (left) | Communication Stack (right)" style="text;html=1;align=left;fontSize=10;fontColor=#666666;" vertex="1" parent="1">
          <mxGeometry x="1020" y="1145" width="800" height="30" as="geometry"/>
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
