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
- 데이터 스냅샷을 올릴 `gh auth login`으로 로그인한
  [GitHub CLI](https://cli.github.com/)

## 공개되는 것

`firm-export-site`가 쓰는 `frontend/static-site/`의 모든 내용입니다.

- 기업별 `summary.md`(AI 생성 표시 포함)와 세분류
- CSV 내보내기(모든 행에 AI 생성 표시)
- 지도 화면과 그 데이터(공개된 병무청 명단), 그리고 Kakao **JavaScript** 키

절대 포함되지 않는 것: `raw_search.json`(수집한 웹 페이지), `webpage.json`, `.env`,
`config.yml`, 모든 서버용 키. 이 폴더는 Git에서 제외되며 업로드로만 PC 밖으로 나갑니다.
저장소 `site-data` 릴리스의 `static-site.tar.gz` 파일로 올라가 Vercel이 빌드할 때
내려받고([자동 배포](#자동-배포)), `scripts/publish_site_data.sh`가 올리는 배포에도
담깁니다. 저장소가 공개라면 이 릴리스 파일도 공개입니다.

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
2. **저장소로 Vercel 프로젝트를 만듭니다.** Vercel에서 **Add New → Project**로 GitHub
   저장소를 가져오거나, CLI로 만든 프로젝트라면 **Settings → Git → Connect Git
   Repository**를 누릅니다. 그다음 **Settings → Build and Deployment**에서:
   - **Root Directory:** `frontend`. **Include files outside the root directory in
     the Build Step**은 켜 두세요. 빌드가 지도 화면의 스크립트와 스타일을 `src/`에서
     가져옵니다.
   - 나머지는 그대로 둡니다. [`frontend/vercel.json`](../frontend/vercel.json)에
     프레임워크, 빌드 명령, 출력 폴더, 라우팅, 아래의 빌드 건너뛰기 규칙이 정해져 있습니다.
     환경 변수는 필요 없습니다.

   프로젝트 이름이 URL이 됩니다. 예를 들어 `firm-analyzer`라는 프로젝트는 이름이 비어
   있다면 `https://firm-analyzer.vercel.app`으로 제공됩니다.
3. **저장소 루트에서 Vercel CLI를 연결합니다.** 내 PC에서 데이터를 배포할 때 씁니다. Root
   Directory가 `frontend`이면 CLI는 루트에서 실행합니다.

   ```bash
   npx vercel login
   npx vercel link
   npx vercel pull --yes --environment=production
   ```

   `.vercel/`(Git 제외)이 만들어집니다. 예전에 만든 `frontend/.vercel/`은 지워도 됩니다.
4. **첫 스냅샷을 올립니다**(`gh auth login` 필요, 최신 `main`에서).

   ```bash
   uv run firm-export-site
   scripts/publish_site_data.sh
   ```

## 배포할 때마다

- **코드:** `frontend/` 안의 내용을 바꾼 커밋이 `main`에 푸시되면 프로덕션에 배포됩니다.
  다른 브랜치, 즉 모든 풀 리퀘스트에서는 미리보기 배포가 만들어지고 Vercel이 PR에 링크를
  남깁니다. `frontend/`를 바꾸지 않은 푸시(Python, 문서, `src/`의 지도 코드)는 빌드하지
  않습니다. 다음 프론트엔드 배포 때 함께 나가거나, `main`에서
  `scripts/publish_site_data.sh`를 실행하면 바로 나갑니다.
- **데이터:** 새 기업을 요약했거나 `firm_results/`에서 기업 폴더를 지운 뒤:

  ```bash
  uv run firm-export-site
  scripts/publish_site_data.sh
  ```

  스크립트가 이후 Git 빌드에 쓸 스냅샷을 올리고, 내 PC에서 빌드해 배포합니다. 배포는
  `origin/main`과 같은 깨끗한 `main`에서만 하므로 프로덕션에는 항상 `main`의 코드가
  올라갑니다. 다른 상태에서는 업로드만 하고 배포 방법을 알려 줍니다. `--no-deploy`를 붙이면
  업로드만 합니다. 지도 화면의 템플릿(`src/firm_analyzer/web/templates/`)이나 Kakao 키를
  바꾼 뒤에도 이렇게 하세요. 그 HTML은 `firm-export-site`가 만듭니다.

`firm-export-site`는 몇 개 기업을 썼는지 출력하고, `KAKAO_JS_API_KEY`가 없으면 경고합니다.

먼저 로컬에서 정적 빌드를 확인하려면:

```bash
cd frontend && npm run build:static && npm run preview:static   # http://localhost:4173
```

직접 배포하려면 저장소 루트에서 실행하세요.

```bash
npx vercel build --prod
npx vercel deploy --prebuilt --prod
```

현재 공개 중인 배포는 `npx vercel ls --prod`로 확인할 수 있습니다.

## 자동 배포

**빌드가 시작되는 조건.** `frontend/vercel.json`에는 빌드 건너뛰기 명령
`git diff --quiet "${VERCEL_GIT_PREVIOUS_SHA:-HEAD^}" HEAD -- .`이 있고, Vercel은 Git
빌드 전에 이를 Root Directory에서 실행합니다. 그 브랜치의 마지막 성공 배포(브랜치의 첫
배포라면 직전 커밋)와 비교해 `frontend/`에 바뀐 것이 없으면 빌드를 건너뜁니다. 비교할 수
없으면 빌드합니다. Vercel은 배포 훅에도 이 규칙을 적용하므로, 데이터는 훅 대신 내 PC에서
배포합니다.

**데이터를 가져오는 방법.** Vercel 서버의 빌드는 저장소에서 시작하는데, 데이터는 커밋하지
않습니다. `firm_results/`와 `frontend/static-site/`에는 실제 기업에 대한 AI 작성 글이
들어 있어서(둘 중 하나라도 추적되면 CI가 실패합니다) 데이터는 따로 전달됩니다. 저장소
`site-data` 릴리스의 `static-site.tar.gz`입니다. `scripts/publish_site_data.sh`가 최신
스냅샷을 묶고, 서버용 키처럼 보이는 것이 있으면 올리지 않으며, 이전 파일을 교체합니다.
`npm run build:static`의 마지막 단계
([`frontend/scripts/copy-static-site.mjs`](../frontend/scripts/copy-static-site.mjs))는
Vercel에 로컬 스냅샷이 없으므로 빌드 중인 저장소(`VERCEL_GIT_REPO_OWNER`,
`VERCEL_GIT_REPO_SLUG`)에서 이 파일을 내려받아 사이트에 넣고, 지도 화면의
스크립트·스타일·명단은 커밋에 있는 것을 씁니다. `SITE_DATA_URL`로 다른 주소를 지정할 수
있습니다. 포크한 저장소는 자체 `site-data` 릴리스가 필요합니다.

릴리스 파일은 커밋과 달리 교체하거나 지울 수 있어 삭제 요청이 모든 곳에 반영됩니다. 빌드는
AI·검색·GitHub 키를 갖지 않고, 파이프라인을 실행하지 않습니다.

`npm run build:static`은 `frontend/dist/`에 일반 정적 사이트를 만들기 때문에 다른 정적
호스팅(Netlify, Cloudflare Pages, GitHub Pages)도 쓸 수 있습니다. `vercel.json`의
rewrite를 그대로 옮기세요. `assets/`, `data/`, `map/`, `static/` 밖의 경로는
`index.html`을 돌려줘야 합니다.

## 기업 삭제하기

정정·삭제 요청을 받으면(이용 안내 화면 참고) `firm_results/`에서 해당 기업 폴더를 지우고
다시 배포하세요(`uv run firm-export-site` 후 `scripts/publish_site_data.sh`, 릴리스 파일도
함께 교체됩니다). 미리보기를 포함한 이전 배포는 각자의 URL로 계속 남아 있으므로, 예전 글을 모든 곳에서
지우려면 Vercel 대시보드(**Deployments → ⋯ → Delete**)나
`npx vercel remove <배포-URL>`로 이전 배포도 삭제하세요.

## 로컬 앱과의 차이

- 검색은 기업 이름, 주소, 요약 본문을 대상으로 합니다. 로컬 서버는 요약의 머리말, 출처
  목록, AI 생성 표시까지 검색하므로 "AI" 같은 단어로 검색하면 기업이 몇 곳 더 나올 수
  있습니다.
- 데이터는 마지막 `firm-export-site` 시점 기준입니다. 대시보드의 새로고침은 같은
  스냅샷을 다시 불러옵니다.
