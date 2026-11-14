# 면책 조항 / Disclaimer

## 한국어

### AI 생성 콘텐츠

Firm Analyzer가 만드는 **기업 요약과 세분류는 AI 언어 모델이 공개 웹 검색 결과를 바탕으로 자동 생성한 참고 자료**입니다.

- 사람이 검토하거나 해당 기업이 확인한 내용이 아닙니다.
- 사실과 다른 내용(이른바 환각), 오래된 정보, 이름이 비슷한 다른 기업의 정보가 섞여 있을 수 있습니다.
- 기업에 대한 평가·추천·순위가 아니며, 기업의 공식 입장을 대변하지 않습니다.
- 지원, 채용, 투자, 전문연구요원 편입 등 중요한 결정 전에는 반드시 기업의 공식 채널과 병무청에서 직접 확인하세요.

각 요약 파일(`summary.md`)과 화면, CSV 내보내기에는 이 사실을 알리는 표시가 붙으며, 요약 아래에는 근거가 된 검색 결과의 출처가 나열됩니다.

### 기업 명단

`data/`의 명단은 병무청이 공개한 「전문연구요원 인원배정 현황」 PDF를 변환한 것입니다. 변환 과정에서 누락이나 오기가 생길 수 있으므로 원본 문서가 우선합니다. 이 프로젝트는 병무청 및 명단에 포함된 어떤 기업과도 관련이 없습니다.

### 보증의 부인

이 소프트웨어와 그 결과물은 있는 그대로(“as is”) 제공되며, 정확성·완전성·최신성·특정 목적 적합성을 포함한 어떠한 보증도 하지 않습니다. 결과물을 근거로 한 판단과 그로 인한 결과에 대한 책임은 이용자에게 있습니다. 자세한 내용은 [LICENSE](LICENSE)를 참고하세요.

### 운영자의 책임

이 도구를 직접 실행하거나 결과를 공개하는 사람(운영자)은 다음을 지켜야 합니다.

- 생성된 결과를 다른 사람에게 보여 줄 때 AI 생성 표시를 제거하지 마세요.
- `raw_search.json`에는 검색으로 수집한 웹 페이지 원문이 들어 있어 개인정보나 타인의 저작물이 포함될 수 있습니다. 공개 저장소나 공개 데이터베이스에 올리지 마세요. (`firm_results/`는 기본적으로 Git에서 제외됩니다.)
- 결과를 공개 서비스로 제공한다면, 기업이 정정·삭제를 요청할 수 있는 연락 수단을 마련하고 요청을 받으면 해당 기업의 결과 폴더를 삭제하세요.
- 사용하는 검색 API와 AI 제공자의 이용 약관을 따르세요.

### 정정·삭제 요청

이 저장소에는 특정 기업에 대한 AI 생성 결과가 포함되어 있지 않습니다. 이 도구로 만든 결과를 공개한 개별 서비스에 관한 요청은 해당 서비스 운영자에게 해 주세요. 저장소 자체에 관한 문의는 GitHub 이슈로 남겨 주세요.

---

## English

### AI-generated content

The **firm summaries and classifications produced by Firm Analyzer are generated automatically by an AI language model from public web search results, for reference only.**

- They are not reviewed by a person or confirmed by the companies concerned.
- They may contain fabricated statements ("hallucinations"), outdated information, or information about a different company with a similar name.
- They are not ratings, recommendations or rankings, and do not represent any company's official position.
- Before any important decision (applying, hiring, investing, or military alternative-service placement), verify with the company's official channels and the Military Manpower Administration (병무청).

Every `summary.md`, every screen that shows a summary, and every CSV export carries a label saying so, and each summary lists the search results it was based on.

### Firm lists

The lists in `data/` are conversions of the 「전문연구요원 인원배정 현황」 PDFs published by the Military Manpower Administration. Conversion can introduce omissions or errors; the original documents take precedence. This project is not affiliated with the Military Manpower Administration or with any company on the lists.

### No warranty

This software and its output are provided "as is", without warranty of any kind, including accuracy, completeness, timeliness or fitness for a particular purpose. You are responsible for any decision you make based on the output. See [LICENSE](LICENSE).

### Operator responsibilities

If you run this tool or publish its output:

- Do not remove the AI-generated label when showing results to others.
- `raw_search.json` holds the text of scraped web pages and can contain personal data or third-party copyrighted material. Do not upload it to a public repository or a publicly readable database. (`firm_results/` is excluded from Git by default.)
- If you publish results as a service, give companies a way to request corrections or removal, and delete that company's result folder when asked.
- Follow the terms of service of the search API and AI providers you use.

### Correction and removal requests

This repository contains no AI-generated output about specific companies. For a service that publishes output made with this tool, contact that service's operator. For the repository itself, open a GitHub issue.
