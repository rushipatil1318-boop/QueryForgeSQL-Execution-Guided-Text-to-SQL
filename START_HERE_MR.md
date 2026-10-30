# इथून सुरू कर — QueryForgeSQL

या project मध्ये आपण साध्या English प्रश्नापासून SQL तयार करतो. उदाहरण: “Which five products generated the highest revenue last month?” Model ला database चा schema देतो. त्याने दिलेली query तपासतो, read-only database वर चालवतो, error आला तर जास्तीत जास्त दोनदा सुधारायला सांगतो.

**Query चालली म्हणजे उत्तर बरोबरच आहे असे नाही.** आपल्या demo मध्ये मुद्दाम असा एक case आहे.

## पायरी 1 — योग्य folder उघड

ZIP `Downloads` मध्ये download कर. तिचे contents `C:\Users\rushi\Downloads\QueryForgeSQL` मध्ये extract कर. या folder मध्ये `README.md`, `requirements.txt`, `queryforgesql`, `scripts` आणि `tests` दिसले पाहिजेत. VS Code मध्ये हाच folder उघड.

खालील block VS Code च्या **PowerShell Terminal** मध्ये paste कर. प्रत्येक command पूर्ण झाल्यावर पुढची command चालव. Python code editor मध्ये या commands paste करायच्या नाहीत.

```powershell
Set-Location -LiteralPath "C:\Users\rushi\Downloads\QueryForgeSQL"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m scripts.check_environment
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m scripts.run_demo
.\.venv\Scripts\python.exe -m scripts.render_report
```

हा block काय करतो: project folder निवडतो, स्वतंत्र `.venv` बनवतो, `SQLGlot` install करतो, environment आणि tests तपासतो, demo चालवतो आणि HTML report बनवतो. स्वतंत्र environment मुळे TinyForgeLM च्या PyTorch setup मध्ये बदल होत नाही. Input म्हणजे repository मधला code आणि स्वतः लिहिलेला teaching data; output म्हणजे `runs\demo` मधले logs आणि report. GPU किंवा API key लागत नाही.

Test run मध्ये `Ran ... tests` नंतर `OK` दिसले पाहिजे. `Ran 0 tests` असेल तर folder चुकीचा आहे. Failure आला तर तिथे थांबून संपूर्ण error पाठव.

## पायरी 2 — report उघड

```powershell
Start-Process -FilePath ".\runs\demo\report.html"
```

ही command तयार झालेली HTML file default browser मध्ये उघडते. यासाठी server किंवा internet लागत नाही. Input: मागील पायरीतील actual run logs. Output: प्रत्येक query, error, repair आणि result पाहता येणारा report.

Demo मध्ये `demo_revenue` ला आधी missing-column error येतो आणि पुढची query चालते. `demo_invalid` ची DELETE query नाकारली जाते. `demo_semantic` ची query चालते, पण चुकीच्या category चे products देते; तिला correctness failure दिसतो. `demo_exhaust` मध्ये तीन generation calls नंतर loop थांबतो.

**हा scripted software demo आहे. LLM वापरलेला नाही आणि हे BIRD accuracy results नाहीत.** त्यावरून “feedback मुळे model सुधारला” असा निष्कर्ष काढायचा नाही.

## पायरी 3 — code समजून घे

सुरुवातीला `docs/LESSONS_MR.md` मधले Lesson 1 आणि `exercises/README.md` मधले Task 1 कर. सर्व files एकदम पाठ करू नकोस. स्वतःचे छोटे function लिहून त्याचा code आणि output पाठव; आपण review करू.

नंतर `docs/MODELS.md` वापरून actual local LLM जोडा. आधी teaching database वर एकच प्रश्न विचारू. तो चालल्यावरच `docs/DATA.md` प्रमाणे real BIRD subset आणि paired evaluation करू. LoRA पुढच्या टप्प्यात आहे.

## सामान्य errors

| Output | अर्थ आणि पुढची कृती |
|---|---|
| `No module named scripts` | Terminal project च्या root मध्ये नाही; पहिली Set-Location command पुन्हा चालव |
| `No module named sqlglot` | `.venv` च्या Python ने `pip install -r requirements.txt` चालव |
| `hard_heap_limit` unsupported | Python मधली SQLite version अपुरी आहे; supported नवीन Python environment वापरून diagnostics पुन्हा चालव |
| `Cannot resume ... code changed` | जुन्या run चे code/config वेगळे आहेत; `--output runs/demo_v2` देऊन नवीन run कर |
| `Model network failure` | actual model service सुरू आहे का आणि config endpoint बरोबर आहे का तपास; scripted demo ला model लागत नाही |
| BIRD download connection reset | downloader तीन प्रयत्न करतो; connection स्थिर झाल्यावर तीच command पुन्हा चालव; TLS verification बंद करू नकोस |

तुझ्या machine वरील actual test/demo output मिळाल्यावरच त्या run ची नोंद report आणि GitHub README मध्ये करू.
