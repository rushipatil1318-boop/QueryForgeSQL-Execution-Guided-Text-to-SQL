# GitHub upload — source release v0.1.0

ही version GitHub वर **source baseline / research in progress** म्हणून upload करण्यासाठी आहे. तुझ्या machine वरील testing सध्या deferred आहे. README आणि reports मध्ये assistant Linux reference checks आणि तुझे अजून न झालेले runs वेगळे नोंदवले आहेत.

## Upload कसा करायचा

1. `QueryForgeSQL.zip` download करून **Extract All** कर.
2. GitHub वर `QueryForgeSQL-Execution-Guided-Text-to-SQL` नावाची नवीन repository तयार कर. Package मध्ये README, LICENSE आणि .gitignore आधीच आहेत.
3. Repository च्या upload screen वर **extract केलेल्या folder मधले files आणि folders** निवड. Repository root मध्ये `README.md`, `requirements.txt`, `queryforgesql/` आणि `scripts/` दिसतील अशी रचना ठेव.
4. `.github/`, `.gitignore`, `.dockerignore` आणि `.env.example` देखील upload मध्ये आले आहेत का पाहा. GitHub browser upload मध्ये फक्त ZIP ठेवली तर code files स्वतंत्रपणे दिसणार नाहीत; source contents upload कर.
5. Commit message: `Add QueryForgeSQL v0.1.0 research baseline`.

Repository description:

Reproducible text-to-SQL baseline with schema retrieval, read-only SQLite execution, bounded repairs and a BIRD evaluation harness. Research in progress.

या ZIP मध्ये code, configs, tests, learning exercises, documentation आणि स्पष्टपणे labelled reference reports आहेत. Raw BIRD database files, model weights, .venv, actual API credentials आणि private run logs दिलेले नाहीत. नंतर generated files जोडताना .gitignore लक्षात ठेव; browser upload करण्यापूर्वी कोणते files निवडले आहेत ते पाहा.

## Status कसा ठेवायचा

- Baseline implementation: available.
- Initial local demo: scripted teaching fixture; LLM accuracy result नाही.
- Earlier assistant Linux checks: `reports/VALIDATION.md` मध्ये नोंदवलेले.
- तुझ्या machine वरील tests आणि actual model run: pending.
- Real BIRD model evaluation, LoRA आणि cloud deployment: pending.

`tests/` आणि GitHub Actions workflow भविष्यातील verification साठी ठेवले आहेत. Upload नंतर workflow चालला तर त्याचा actual result पाहूनच passing CI असा दावा कर. हा source snapshot upload करणं म्हणजे संपूर्ण research study पूर्ण झाली असं नाही.

पुढे काम सुरू करताना `START_HERE_MR.md` आणि `docs/LESSONS_MR.md` वापर. CV मध्ये project ला In progress ठेव; measured results मिळाल्यावर description update कर.

GitHub upload reference: https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository
