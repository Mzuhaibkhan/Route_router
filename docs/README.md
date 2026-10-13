# Route Radar Documentation

Welcome to the comprehensive technical documentation for **Route Radar**, an enterprise-grade commercial freight weather risk engine and multi-fleet dispatch intelligence platform.

---

## Documentation Structure

| Document | Description |
|---|---|
| [System Architecture](architecture.md) | High-level system architecture, component topology, data flow pipelines, caching strategies, and tech stack. |
| [API Reference](api-reference.md) | Full specification of all REST API endpoints for single-route analysis, batch fleet dispatch, live telemetry, and geocoding. |
| [Risk Engine Specification](risk-engine.md) | Deep dive into meteorological risk bands, truck gross weight tipping thresholds, trailer aerodynamic sail factors, and departure window optimization. |
| [Multi-Fleet Management Guide](fleet-management.md) | Guide to organizational tenant hierarchy, vehicle & trailer fleet inventory, high-throughput batch route analysis, and live GPS hazard monitoring. |
| [Production Deployment Guide](deployment.md) | Instructions for deploying to Render via Blueprint/Docker, local container orchestration, WhiteNoise single-origin static serving, and environment configuration. |
| [Frontend Architecture & UI](frontend.md) | Overview of the React 19 SPA, brutalist dark design system, React-Leaflet concurrent mapping, Lenis smooth scrolling, Three.js WebGL particle constellation, and GSAP kinetic animations. |
| [Testing & Quality Assurance](testing.md) | Testing philosophy, test suite coverage (122 Pytest tests, 17 Vitest tests, 100% passing), floating-point boundary tests, and GitHub Actions CI pipeline. |
| [Loom Video Presentation Guide](loom_speech.md) | Complete 5-to-6 minute technical demonstration script, timestamps, visual cues, and presenter guide. |

---

## Project Overview

Route Radar is engineered to solve a critical commercial transportation challenge: **catastrophic truck rollovers and transit delays caused by localized severe weather events**.

### Core Value Proposition

1. **Precision Atmospheric Sampling**: Samples commercial highway corridors at 25-mile intervals (or 10/50 miles) and matches each coordinate against 49-hour hourly forecasts from Open-Meteo.
2. **Physics-Based Load Tipping Rules**: Dynamically alters rollover hazard thresholds based on tractor-trailer gross weight (1,000 to 80,000 lbs) and trailer aerodynamic profile (`DRY_VAN`, `REEFER`, `FLATBED`, `TANKER`).
3. **Multi-Route Comparative Analysis**: Evaluates primary and alternative interstate routes (via OpenRouteService) to identify safer diversions around severe storm cells.
4. **Optimal Departure Advisory**: Scans a ?6-hour departure horizon to find weather windows that reduce or eliminate extreme wind and precipitation exposure.
5. **Multi-Fleet Telemetry & Command Center**: Supports enterprise carriers with multi-tenant organizational fleets, batch dispatching of up to 500 loads, real-time nationwide risk clustering, and live alert feeds.

---

## Quick Navigation

- Looking to run Route Radar locally? See the [Local Setup in Deployment Guide](deployment.md#local-development-setup).
- Integrating via REST API? Read the [API Reference](api-reference.md).
- Understanding how rollover risk is computed? Check the [Risk Engine Specification](risk-engine.md).
- Exploring the UI design and animations? See [Frontend Architecture](frontend.md).
