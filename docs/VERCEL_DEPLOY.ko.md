# Vercel에 뷰어 공개하기

[English](VERCEL_DEPLOY.md) · **한국어**

호스팅되는 사이트는 뷰어의 **읽기 전용 정적 사본**입니다. 대시보드, 기업 검색, 요약,
지도, CSV 다운로드가 들어 있습니다. 파이프라인, 설정, 명단 관리 화면은 파일을 바꾸고
API 사용량을 쓰는 작업을 시작하기 때문에 빠져 있습니다. 이 기능들은 계속 로컬에서
`uv run firm-app`으로 실행하세요.

Vercel에는 Flask 서버가 없습니다. `firm-export-site`가 API의 응답을 파일로 저장하고,
프론트엔드의 정적 빌드가 브라우저 안에서 그 파일들을 검색합니다.

> [!TIP]
> 결과물을 먼저 보고 싶다면, 이 프로젝트의 사이트가
> **<https://firm-analyzer.vercel.app>** 에서 운영 중입니다. 아래와 똑같은 절차로
> 배포했습니다.

## 준비물

- [빠른 시작](../README.ko.md#빠른-시작)대로 설정한 로컬 앱(Python 3.12 이상, uv,
  Node.js 22 이상)
- [파이프라인](../README.ko.md#파이프라인-실행)으로 만든 `firm_results/`의 요약
- [Vercel](https://vercel.com/signup) 계정(무료 Hobby 플랜으로 충분)
- 선택, 지도용: [Kakao Developers](https://developers.kakao.com/console/app)에 만든
  앱과 그 **JavaScript** 키. `.env`에 `KAKAO_JS_API_KEY`로 넣습니다.
  ([KOREAN_MAPS_SETUP.md](KOREAN_MAPS_SETUP.md)의 REST 키는 지오코딩 전용이며 내 PC에만
  남습니다.)
- 선택, [자동 배포](#자동-배포)용: `gh auth login`으로 로그인한
  [GitHub CLI](https://cli.github.com/)

## 공개되는 것

`firm-export-site`가 쓰는 `frontend/static-site/`의 모든 내용입니다.

- 기업별 `summary.md`(AI 생성 표시 포함)와 세분류
- CSV 내보내기(모든 행에 AI 생성 표시)
- 지도 화면과 그 데이터(공개된 병무청 명단), 그리고 Kakao **JavaScript** 키

절대 포함되지 않는 것: `raw_search.json`(수집한 웹 페이지), `webpage.json`, `.env`,
`config.yml`, 모든 서버용 키. 이 폴더는 Git에서 제외되며 업로드로만 PC 밖으로 나갑니다.
Vercel로, 그리고 [자동 배포](#자동-배포)를 쓰면 저장소 `site-data` 릴리스의
`static-site.tar.gz` 파일로 올라갑니다. 저장소가 공개라면 이 파일도 공개입니다.

> [!IMPORTANT]
> 실제 기업에 대해 AI가 쓴 글을 공개하는 것입니다. AI 생성 표시를 유지하고, 기업이
> 연락할 수단을 마련하며, 요청이 오면 해당 기업을 삭제하세요([기업 삭제하기](#기업-삭제하기)).
> [DISCLAIMER.md](../DISCLAIMER.md)의 '운영자의 책임'을 참고하세요.

## 최초 1회 설정

1. **Kakao 키를 내 사이트로 제한합니다.** Kakao Developers
   (<https://developers.kakao.com/console/app>)에서 앱을 열고
   **앱 → 플랫폼 키 → JavaScript 키 → JavaScript SDK 도메인**(예전 이름 "사이트
   도메인")에 `https://<프로젝트>.vercel.app`과 사용할 커스텀 도메인을 추가합니다.
   경로 없이 출처(origin)만 입력하세요. 등록하기 전까지 지도 화면에는 지도 대신 기업
   목록과 "지도를 로드할 수 없습니다" 메시지가 표시됩니다. 정확한 URL은 첫 배포 후에
   알 수 있으니 이 단계는 나중에 해도 됩니다.
2. **frontend 폴더를 Vercel 프로젝트에 연결합니다.**

   ```bash
   cd frontend
   npx vercel login
   npx vercel link
   npx vercel pull --yes --environment=production
   ```

   `vercel link`가 프로젝트를 만들고 `frontend/.vercel/`(Git 제외)을 생성합니다.
   [`frontend/vercel.json`](../frontend/vercel.json)에 빌드 명령, 출력 폴더, 라우팅이
   정해져 있으므로 제안되는 기본값을 그대로 쓰면 됩니다. 프로젝트 이름이 URL이 됩니다.
   예를 들어 `firm-analyzer`라는 프로젝트는 이름이 비어 있다면
   `https://firm-analyzer.vercel.app`으로 제공됩니다. Vercel에 환경 변수를 설정할 필요는
   없습니다.

## 배포할 때마다

새 기업을 요약했거나 `firm_results/`에서 기업 폴더를 지운 뒤에는 데이터를 스냅샷으로
저장하고 올립니다. [자동 배포](#자동-배포)를 설정했다면 다음 두 줄이면 됩니다.

```bash
uv run firm-export-site
scripts/publish_site_data.sh     # 스냅샷을 올리고 Deploy 워크플로를 시작
```

프론트엔드나 지도 화면의 코드 변경은 명령이 필요 없습니다. `main`에 병합되면 배포됩니다.
자동 배포 없이 직접 빌드하고 올리려면:

```bash
uv run firm-export-site
cd frontend
npx vercel build --prod
npx vercel deploy --prebuilt --prod
```

`firm-export-site`는 몇 개 기업을 썼는지 출력하고, `KAKAO_JS_API_KEY`가 없으면 경고합니다.
`vercel build`는 내 PC에서 빌드하고, `--prebuilt`는 그 결과만 업로드합니다. 마지막 명령이
배포 URL을 출력하며, 프로덕션 URL이 새 배포를 가리키게 됩니다.

먼저 로컬에서 정적 빌드를 확인하려면:

```bash
cd frontend && npm run build:static && npm run preview:static   # http://localhost:4173
```

현재 공개 중인 배포는 `frontend/`에서 `npx vercel ls --prod`로 확인할 수 있습니다.

## 자동 배포

[`.github/workflows/deploy.yml`](../.github/workflows/deploy.yml)은 `main`에 푸시될 때
`frontend/`나 지도 화면의 스크립트·스타일(`src/firm_analyzer/web/static/`)이 바뀌었으면
프로덕션에 배포합니다. 직접 시작할 수도 있습니다(**Actions → Deploy → Run workflow**, 또는
`gh workflow run deploy.yml`).

데이터는 Git에 없으므로 워크플로가 내려받습니다. `site-data` 릴리스의
`static-site.tar.gz`이고, `scripts/publish_site_data.sh`가 최신 `firm-export-site`
스냅샷으로 바꿔 올립니다. 릴리스 파일은 교체하거나 지울 수 있어 삭제 요청이 모든 곳에
반영됩니다. 스냅샷을 커밋하면 모든 요약이 Git 기록에 영원히 남습니다. 워크플로는 수동 배포와
똑같이 Vercel CLI로 빌드하고, 지도 화면의 스크립트·스타일·명단은 배포하는 커밋의 것을
씁니다.

### 한 번만 설정하기

1. **Vercel 토큰 만들기**: <https://vercel.com/account/tokens>에서 프로젝트가 속한 팀
   범위로 만듭니다. 비밀번호처럼 다루세요.
2. **저장소 시크릿 세 개 추가**(**Settings → Secrets and variables → Actions**), 또는
   저장소 루트에서 GitHub CLI로:

   ```bash
   gh secret set VERCEL_TOKEN                     # 물으면 토큰을 붙여 넣기
   gh secret set VERCEL_ORG_ID --body "$(node -p "require('./frontend/.vercel/project.json').orgId")"
   gh secret set VERCEL_PROJECT_ID --body "$(node -p "require('./frontend/.vercel/project.json').projectId")"
   ```

   두 ID는 `vercel link`가 만든 `frontend/.vercel/project.json`에 있습니다.
3. **첫 스냅샷 올리기**(`gh auth login` 필요):

   ```bash
   uv run firm-export-site
   scripts/publish_site_data.sh --no-deploy
   ```

   워크플로 파일이 `main`에 들어간 뒤에는 `--no-deploy`를 빼세요. 스크립트가 배포까지
   시작합니다.

시크릿이나 릴리스 파일이 없으면 워크플로가 이유를 알려 주며 실패합니다. 워크플로는
파이프라인을 실행하지 않고, AI·검색 API 키도 갖지 않습니다.

### 새 스냅샷이 필요한 경우

Kakao JavaScript 키가 들어간 지도 화면의 HTML은 `firm-export-site`가 만듭니다.
`src/firm_analyzer/web/templates/`나 키를 바꿨다면
`uv run firm-export-site && scripts/publish_site_data.sh`를 실행하세요.

### Vercel 자체 Git 빌드를 꺼 두는 이유

Vercel 서버에서 빌드하면 저장소에서 시작하는데, 저장소에는 `firm_results/`가 없어 빈
뷰어가 공개됩니다. 그래서 `vercel.json`은 `git.deploymentEnabled: false`를 유지하고,
"Deploy with Vercel" 버튼도 제공하지 않습니다. 위 워크플로는 데이터를 더해 GitHub에서
빌드하고, 직접 배포할 때와 같은 방식으로 결과를 올립니다.

`npm run build:static`은 `frontend/dist/`에 일반 정적 사이트를 만들기 때문에 다른 정적
호스팅(Netlify, Cloudflare Pages, GitHub Pages)도 쓸 수 있습니다. `vercel.json`의
rewrite를 그대로 옮기세요. `assets/`, `data/`, `map/`, `static/` 밖의 경로는
`index.html`을 돌려줘야 합니다.

## 기업 삭제하기

정정·삭제 요청을 받으면(이용 안내 화면 참고) `firm_results/`에서 해당 기업 폴더를 지우고
다시 배포하세요(`uv run firm-export-site` 후 `scripts/publish_site_data.sh`, 릴리스 파일도
함께 교체됩니다). 이전 배포는 각자의 URL로 계속 남아 있으므로, 예전 글을 모든 곳에서
지우려면 Vercel 대시보드(**Deployments → ⋯ → Delete**)나
`npx vercel remove <배포-URL>`로 이전 배포도 삭제하세요.

## 로컬 앱과의 차이

- 검색은 기업 이름, 주소, 요약 본문을 대상으로 합니다. 로컬 서버는 요약의 머리말, 출처
  목록, AI 생성 표시까지 검색하므로 "AI" 같은 단어로 검색하면 기업이 몇 곳 더 나올 수
  있습니다.
- 데이터는 마지막 `firm-export-site` 시점 기준입니다. 대시보드의 새로고침은 같은
  스냅샷을 다시 불러옵니다.
