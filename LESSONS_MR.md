# QueryForgeSQL — छोटे lessons

प्रत्येक lesson मध्ये आधी concept समजून घे, मग संबंधित file वाच आणि शेवटी छोटा task कर. एकाच दिवशी सर्व code पाठ करायची गरज नाही. Model training, LoRA आणि deployment हे पुढचे विषय आहेत.

## Lesson 1 — Text-to-SQL म्हणजे काय?

Database मध्ये माहिती tables मध्ये असते. `products` मध्ये product चे नाव आहे, `orders` मध्ये तारीख आहे आणि `order_items` मध्ये कोणता product किती विकला गेला ते आहे. Schema म्हणजे या tables/columns चा नकाशा. Foreign key म्हणजे दोन tables जोडणारा संबंध.

“Revenue किती?” या प्रश्नासाठी `quantity * unit_price` लागते. फक्त product नाव पाहून उत्तर मिळत नाही; संबंधित tables join करावे लागतात. `last month` साठी reference date ठरवावी लागते. आपल्या teaching data मध्ये reference date `2026-10-30` आहे; म्हणून September 2026 चे orders निवडतो. महिन्याच्या पहिल्या तारखेपासून पुढच्या महिन्याच्या पहिल्या तारखेच्या आधीपर्यंत filter ठेवतो.

```sql
SELECT COUNT(*) FROM orders;
```

हा SQL block orders मधल्या rows मोजतो. Counting शिकण्यासाठी हा सर्वात छोटा baseline आहे. Input: `orders` table. Output: एक row, एक number; teaching database मध्ये तो `5` आहे. हे model accuracy चे metric नाही, database query चे उत्तर आहे.

वाचायची file: `scripts/prepare_demo.py`. पहिला task: प्रत्येक table मधला primary/foreign key स्वतः लिहून काढ. Revenue प्रश्नात `customers` table का आवश्यक नाही ते सांग.

## Lesson 2 — Schema retrieval का?

मोठ्या database चा संपूर्ण schema prompt मध्ये दिला तर prompt लांब होतो आणि model गोंधळू शकतो. Retrieval प्रश्नाशी संबंधित table/column names निवडते. आपला पहिला retriever साधा lexical आहे: प्रश्नातील words आणि schema मधले words जुळवतो. कमी tables मध्ये दिसणाऱ्या words ला थोडे अधिक महत्त्व देतो. हे embedding model नाही.

Input: प्रश्न + full schema dictionary. Output: निवडलेले tables, columns, foreign keys, त्यांचे scores आणि model ला दाखवायचा text. Primary/foreign keys जपतो, कारण ते join साठी उपयोगी असतात. दोन निवडलेल्या tables मध्ये bridge table लागल्यास जास्तीत जास्त एक extra bridge घेतो. सर्व join paths मिळतील याची हमी नाही.

वाचायची file: `queryforgesql/retrieval.py`. Task: `schema_top_k` कमी केल्यावर revenue query साठी आवश्यक table गायब होते का ते report मधल्या `retrieval` field मध्ये पाहा. बदलासाठी नवीन run directory वापर. Accuracy बद्दल निष्कर्ष काढण्यापूर्वी वास्तविक model/data लागेल.

## Lesson 3 — Model output लगेच execute का करू नये?

Model कधी malformed SQL किंवा DELETE सारखी query देऊ शकतो. फक्त string `SELECT` ने सुरू होते का हे तपासणे पुरेसे नाही. दोन statements असू शकतात किंवा CTE मध्ये दुसरे operation असू शकते. SQLGlot text ला AST म्हणजे query ची रचना बनवते. आपण त्या रचनेत अनुमती असलेले operations तपासतो.

Input: model ने दिलेला SQL text. Output: त्याच SQL ला permission, किंवा स्पष्ट `ValidationError`. Validator SQL चे अर्थ बदलून दुसरी query बनवत नाही. Runtime मध्ये SQLite authorizer पुन्हा actual table/function access तपासतो.

वाचायची file: `queryforgesql/validation.py` आणि `tests/test_validation.py`. Task: तीन safe आणि तीन unsafe query examples लिही; execute न करता validator कसा निर्णय घेतो ते समजाव. Unsafe query स्वतःच्या actual database वर चालवू नकोस; tests साठी temporary teaching database आहे.

## Lesson 4 — Read-only execution आणि limits

Read-only म्हणजे model ला records बदलता येत नाहीत. पण एखादी SELECT query खूप वेळ किंवा memory वापरू शकते. म्हणून row limit, byte limit, SQLite heap limit, progress deadline आणि parent timeout लावले आहेत. Linux वर process CPU/address-space limitsही आहेत; Windows वर तोच OS memory cap लागू असल्याचा दावा आपण करत नाही.

Input: approved offline database file + validated SQL. Output: complete rows/columns किंवा failure status. Partial result मिळाल्यावर त्याला full correct answer म्हणायचे नाही; म्हणून row/byte cap ओलांडला तर scoring साठी partial rows परत करत नाही.

वाचायच्या files: `sandbox.py`, `worker.py`, `docs/EXECUTION_BOUNDARY.md`. Task: `row_limit`, `timeout`, `validation_error` आणि `ok` यांत काय फरक आहे ते प्रत्येकी एका वाक्यात लिही.

## Lesson 5 — Bounded repair loop

पहिली SQL query चुकीच्या column चे नाव वापरते, असे समज. Database `no such column` error देतो. आपण model ला त्याची आधीची query आणि actual error देतो. Model नवीन query सुचवतो. जास्तीत जास्त दोन repairs देतो; म्हणजे एकूण तीन generation calls.

Input: प्रश्न, retrieved schema, model आणि मागचा error. Output: पहिली executable query किंवा repair budget संपल्याचा failure. Database error हे feedback आहे; gold SQL किंवा evaluation score feedback नाही.

Query execute झाली की loop थांबतो. ती चुकीच्या category चे products देत असली तरी model ला “उत्तर चुकलं” असे आपल्या evaluator कडून गुपचूप सांगत नाही. अन्यथा संशोधनात answer leakage होईल. Empty result देखील नेहमी error नसतो.

वाचायची file: `queryforgesql/pipeline.py`. Task: `demo_revenue`, `demo_semantic`, `demo_empty`, `demo_exhaust` यांना किती calls लागले ते report मध्ये शोध. प्रत्येक case मध्ये loop का थांबला ते स्वतः लिही.

## Lesson 6 — Execution accuracy आणि semantic correctness

Held-out प्रश्नासाठी आपल्या generated SQL चे result आणि reference SQL चे result compare करतो. Reference query generation पूर्ण झाल्यावरच चालते. Matching result हा उपयोगी signal आहे, पण एका snapshot वर दोन चुकीच्या/वेगळ्या queries योगायोगाने सारखे result देऊ शकतात. म्हणून semantic error analysisही लागते.

```python
from collections import Counter

predicted = [("Pen",)]
reference = [("Pen",), ("Pen",)]

print(set(predicted) == set(reference))
print(Counter(predicted) == Counter(reference))
```

हा Python block unique rows आणि duplicate counts यातील फरक दाखवतो. Evaluation चा अर्थ समजण्यासाठी तो लागतो. Input: एका बाजूला Pen एकदा, दुसऱ्या बाजूला दोनदा. Output: पहिल्या print ला `True`, दुसऱ्याला `False`. `set` duplicates विसरतो; `Counter` प्रत्येक row कितीदा आहे ते जपतो. हा block Python file किंवा `python` interpreter मध्ये चालव; थेट PowerShell command म्हणून paste करू नकोस.

Reference ला top-level `ORDER BY` असेल तर आपल्या strict metric मध्ये क्रमही तपासतो. समान sort keys असतील तर tie order अस्पष्ट असू शकतो; अशा failures ची manual review कर. BIRD-style set metric वेगळा ठेवतो आणि त्याला strict metric म्हणून मांडत नाही.

वाचायची file: `queryforgesql/evaluation.py`. Task: `ORDER BY` असलेल्या reference साठी उलट क्रमाचा result strict metric मध्ये का fail व्हायला पाहिजे ते समजाव.

## Lesson 7 — Reproducibility

Seed generation मधील randomness नियंत्रित करण्याचा प्रयत्न करतो. पण वेगळे model versions, quantization, hardware किंवा APIs यांवर तो exact समान output देईलच असे नाही. म्हणून config, code hash, data hashes, environment, model digest, prompts आणि actual outputs जतन करतो.

`predictions.jsonl` मध्ये प्रत्येक पूर्ण case स्वतंत्र line म्हणून save होतो. Program थांबला तर त्याच configuration चा पुढचा run पूर्ण झालेले cases वगळतो. Code/config/data बदलल्यावर resume नाकारतो; नवीन run folder देतो. Model training नसल्यामुळे हा LoRA checkpoint नाही; हे evaluation progress saving आहे.

Task: seed 42 चा demo एकदा चालवून पुन्हा त्याच output folder वर चालव. `predictions.jsonl` मधले records दुप्पट झाले नाहीत हे पाहा. Scripted responses असल्यामुळे या demo मधील seed comparison ला LLM randomness study समजू नकोस.

## प्रत्येक core file चे input → output

| File | Input | Output | का लागते |
|---|---|---|---|
| `config.py` | JSON settings | validated dataclasses | silent config mistakes टाळायला |
| `data.py` | question files, snapshots | examples, hashes, split checks | data provenance आणि leakage checks साठी |
| `worker.py` schema action | offline DB | tables/columns/keys | model ला database नकाशा द्यायला |
| `retrieval.py` | question + schema | selected schema text | prompt मध्ये संबंधित माहिती द्यायला |
| `prompts.py` | public question + retrieved schema | messages | model ला स्पष्ट instructions द्यायला |
| `providers.py` | messages + seed | SQL response + known usage | actual model किंवा explicit fixture जोडायला |
| `validation.py` | SQL text | permission/error | generated SQL चे operations तपासायला |
| `sandbox.py`, `worker.py` | DB path + SQL | bounded rows/error | read-only query execution साठी |
| `pipeline.py` | question + model + runner | attempts + final result | जास्तीत जास्त दोन repairs साठी |
| `evaluation.py` | candidate/reference results | named scores | query चालणे आणि उत्तर जुळणे वेगळे मोजायला |

आधी Lesson 1 चे उत्तर आणि exercise मधला छोटा बदल कर. मग एकावेळी एक module समजून घेऊन पुढे जाऊ.
