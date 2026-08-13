# Fénix: A Holonic MOM System with Activity-Based Timed Place Petri Nets

Fénix is a lightweight **Manufacturing Operations Management (MOM)** system designed specifically for Small and Medium-sized Enterprises (SMEs). It implements a **holonic Product-Process-Resource (PPR)** architecture and uses **Activity-Based Timed Place Petri Nets (AB-TPPNs)** as its execution tracking and cost-optimal scheduling engine.

---

## 📖 Scientific Publications

Fénix is developed as part of an academic research project at **Universidad de los Andes (ULA), Mérida, Venezuela**. Its theoretical bases and empirical results are detailed in two companion articles:

1.  **Part I: Conceptual Bases and Optimization**  
    *Title:* "A Holonic PPR Framework and Petri Net Formalism for Cost-Optimal Production Scheduling in SMEs"  
    *Focus:* Formal definition of the AB-TPPN mathematical model, path-dependence of production costs under resource yield limits, and the Branch-and-Bound scheduling engine.
2.  **Part II: SCADA Integration and Empirical Validation**  
    *Title:* "SCADA-Driven Model Calibration, Condition Monitoring, and Empirical Cost Verification in Holonic Manufacturing"  
    *Focus:* Real-time parameter calibration using live SCADA timestamps via an EWMA estimator, non-intrusive degradation tracking using the Energy Deviation Ratio (EDR), and validation on a 14-month dataset of 10,089 production orders.

---

## 🚀 Key Features

*   **Distributed Autonomy (Holonic Design):** Replaces rigid hierarchical vertical control (classic ISA-95) with cooperative, autonomous agents representing Resources, Products, and Orders.
*   **Cost-Optimal Scheduling:** Minimizes true production cost (Energy, Labor, Depreciation, and Material Yield Loss) under a hard delivery deadline.
*   **SCADA-Driven Calibration:** Automatically calibrates nominal processing durations and energy rates from shop-floor execution logs using a dual-timescale EWMA loop.
*   **Non-Intrusive Condition Monitoring:** Detects resource wear and tear through an Energy Deviation Ratio (EDR) and automatically adjust resource competitiveness.
*   **High Resiliency (Fault-Tolerance):** State recovery reconstructed automatically from transactional database Petri markings in case of server failures.

---

## 🛠️ Getting Started (For Enterprises)

Fénix is designed to be accessible to plant engineers without formal programming or Petri net expertise. The plant configuration is specified through two simple interfaces:

1.  **Static Data (Excel Templates):**
    Specify resources (machines, operators, hourly cost rates), product taxonomies, and bills of materials (BOM) in a standard Excel spreadsheet.
2.  **Process Flow Logic (YAML Scripts):**
    Write a simple YAML file declaring the operational steps and coordination handshakes:
    ```yaml
    proceso:
      estaciones:
        - dispersor_espera
        - dispersor_mezclando
        - diluidor_espera
      acciones:
        iniciar_mezcla:
          cuando: [dispersor_espera]
          mueve_a: [dispersor_mezclando]
          tipo: "Manual"
        unir_con_diluidor:
          cuando: [dispersor_mezclando, diluidor_espera]
          mueve_a: [diluidor_recibiendo]
          tipo: "Sincronizado"
    ```

---

## 📂 Repository Structure

*   [`fenix/`](file:///C:/Users/echac/Documents/gemini/sgo/fenix/): Source code of the Python execution engine, database schemas, and web interfaces.
    *   [`servicios/`](file:///C:/Users/echac/Documents/gemini/sgo/fenix/servicios/): Orchestrator, scheduler, and resource condition validator.
    *   [`utils/motor_abtppn.py`](file:///C:/Users/echac/Documents/gemini/sgo/fenix/utils/motor_abtppn.py): Mathematical Petri net simulation engine.
*   [`Filosofia_Integracion_Holonica.md`](file:///C:/Users/echac/Documents/gemini/sgo/Filosofia_Integracion_Holonica.md): Introductory philosophy on holonic systems and the historical transition from hierarchical control layers (PDVSA project context).
*   [`Manual_Tecnico_Final_MOM.md`](file:///C:/Users/echac/Documents/gemini/sgo/Manual_Tecnico_Final_MOM.md): Technical architecture manual (DB design, event triggers, APIs).
*   [`Manual_Usuario_MOM.md`](file:///C:/Users/echac/Documents/gemini/sgo/Manual_Usuario_MOM.md): User guide for plant configuration and operation.
*   [`FenixDescripcionGeneral.md`](file:///C:/Users/echac/Documents/gemini/sgo/FenixDescripcionGeneral.md), [`FILOSOFIA.md`](file:///C:/Users/echac/Documents/gemini/sgo/FILOSOFIA.md), [`FLUJO_DATOS.md`](file:///C:/Users/echac/Documents/gemini/sgo/FLUJO_DATOS.md), [`geminiInicio.md`](file:///C:/Users/echac/Documents/gemini/sgo/geminiInicio.md), [`Glosario_de_Terminos.md`](file:///C:/Users/echac/Documents/gemini/sgo/Glosario_de_Terminos.md): Additional design philosophy, data flow specifications, and terminology glossaries.

---

## 🎓 Citation

If you use Fénix in your academic research, please cite the companion papers:

```bibtex
@article{ChaconCardillo2026_PartI,
  author  = {Chac{\'o}n, Edgar and Cardillo, Juan},
  title   = {A Holonic PPR Framework and Petri Net Formalism for Cost-Optimal Production Scheduling in SMEs},
  journal = {Computers in Industry},
  year    = {2026},
  note    = {Under review}
}

@article{ChaconCardillo2026_PartII,
  author  = {Chac{\'o}n, Edgar and Cardillo, Juan},
  title   = {SCADA-Driven Model Calibration, Condition Monitoring, and Empirical Cost Verification in Holonic Manufacturing},
  journal = {Computers in Industry},
  year    = {2026},
  note    = {Under review}
}
```

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.
