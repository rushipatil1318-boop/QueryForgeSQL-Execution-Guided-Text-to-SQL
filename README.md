# QueryForgeSQL — Execution-Guided Text-to-SQL

**Status:** learning and research baseline; actual-model and BIRD database evaluation are pending.

The project converts natural-language questions to SQLite queries using schema retrieval, SQLGlot validation, bounded read-only execution and at most two repair attempts. A scripted six-question demonstration exercises execution errors, unsafe queries and incorrect but executable answers. Its outcomes are software tests, not model accuracy.

Start with the repository's `START_HERE_MR.md` guide. Read `VALIDATION.md` for the assistant-generated reference-run provenance and scope, and `EXPERIMENTS.md` for the planned controlled comparison. The exercises below remain part of the learning project.

## छोटे implementation tasks

Working baseline आधी चालव. Exercises स्वतंत्र आहेत; production files delete करण्याची गरज नाही. `lesson01.py` मध्ये working reference दिली आहे. बदल करण्यापूर्वी ती समजून घे.

## Task 1 — स्वतः duplicate counting लिही

VS Code मध्ये `exercises/lesson01.py` उघड. `bag_equal` मधला `Counter` वापर काढून दोन साधे dictionaries आणि `for` loops वापरून तसाच result मिळव. Function signature कायम ठेव. Input lists बदलू नकोस. हे SQL result मधले duplicates का महत्त्वाचे आहेत ते शिकवते.

Input: दोन lists of hashable row tuples. Output: counts समान असतील तर `True`, नाहीतर `False`. उदाहरण: `[(1,), (2,)]` आणि `[(2,), (1,)]` match; `[(1,)]` आणि `[(1,), (1,)]` mismatch.

```powershell
.\.venv\Scripts\python.exe -m exercises.check_lesson01
```

ही command तुझ्या function वर चार checks चालवते: row order, duplicate counts, empty inputs आणि input mutation. Input: तुझा saved `lesson01.py`. Output: चार tests आणि `OK`, किंवा सुधारायची failure. हा **Terminal command** आहे; Python function file मध्ये paste करायचा नाही. बदललेला function आणि output review साठी पाठव.

## पुढचे tasks, एकावेळी एक

2. `tests/test_validation.py` मध्ये एक नवीन safe CTE आणि एक unsafe multi-statement case add कर. तो test एखादा खरा behavior तपासत आहे याची खात्री कर.
3. Schema retrieval मध्ये एक संबंधित column का निवडला गेला ते शब्द/score वापरून समजाव. नवीन retrieval method स्वतंत्र config/run मध्ये compare कर.
4. `demo_semantic` ची executable पण चुकीची query loop का दुरुस्त करत नाही ते लिही. Gold SQL repair prompt मध्ये टाकू नकोस.
5. Real-model teaching run मधला एक failure inspect करून error category लिही. स्वतःचे actual observations वापर; fixture scores ला BIRD results म्हणू नकोस.

README/learning log मध्ये तुझे experiments आणि तू समजावू शकणारे बदल नोंदव. Code स्वतः समजून बदलणे आणि त्याचे पुरावे दाखवणे हे portfolio साठी उपयोगी आहे.
