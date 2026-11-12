import AiNotice from '../components/AiNotice';

/** 이용 안내 및 면책 조항. The same text is in DISCLAIMER.md at the repository root. */
export default function About() {
  return (
    <div className="glass-card prose-page">
      <div className="page-header">
        <h2 className="page-title">이용 안내 및 면책 조항</h2>
        <p className="page-subtitle">Firm Analyzer가 보여 주는 정보의 성격과 한계</p>
      </div>

      <AiNotice />

      <section aria-labelledby="about-what">
        <h3 className="section-title" id="about-what">어떤 정보인가요</h3>
        <ul>
          <li>
            <strong>기업 명단</strong>은 병무청이 공개한 「전문연구요원 인원배정 현황」을 그대로 옮긴
            것입니다. 변환 과정에서 누락·오기가 생길 수 있으므로 원본 문서가 우선합니다.
          </li>
          <li>
            <strong>기업 요약과 세분류</strong>는 이 도구가 웹 검색(Tavily)으로 찾은 공개 자료를 AI
            언어 모델이 자동으로 요약·분류한 결과입니다. 사람이 검토하거나 기업이 확인한 내용이
            아닙니다.
          </li>
          <li>각 요약 아래의 <strong>출처</strong> 목록에서 원문을 직접 확인할 수 있습니다.</li>
        </ul>
      </section>

      <section aria-labelledby="about-limits">
        <h3 className="section-title" id="about-limits">한계와 주의 사항</h3>
        <ul>
          <li>AI는 사실이 아닌 내용을 그럴듯하게 만들어 내거나(환각), 이름이 비슷한 다른 기업의 정보를 섞을 수 있습니다.</li>
          <li>검색 시점 이후 바뀐 사업 내용, 채용 여부, 조직 정보는 반영되지 않습니다.</li>
          <li>요약과 분류는 기업에 대한 평가·추천·순위가 아니며, 기업의 공식 입장을 대변하지 않습니다.</li>
          <li>전문연구요원 편입·채용 여부는 반드시 병무청과 해당 기업에 직접 확인하세요.</li>
        </ul>
      </section>

      <section aria-labelledby="about-disclaimer">
        <h3 className="section-title" id="about-disclaimer">면책</h3>
        <p>
          이 도구와 그 결과물은 있는 그대로(&ldquo;as is&rdquo;) 제공되며, 정확성·완전성·최신성을
          보증하지 않습니다. 결과물을 근거로 한 판단과 그 결과에 대한 책임은 이용자에게 있습니다. 이
          프로젝트는 병무청 및 명단에 포함된 어떤 기업과도 관련이 없습니다.
        </p>
      </section>

      <section aria-labelledby="about-corrections">
        <h3 className="section-title" id="about-corrections">정정·삭제 요청</h3>
        <p>
          기업 관계자로서 잘못된 내용의 정정이나 삭제를 원하시면 이 서비스를 운영하는 사람에게
          알려 주세요. 오픈소스 저장소에 관한 요청은 GitHub 이슈로 남겨 주시면 됩니다. 운영자는
          해당 기업의 결과 폴더를 삭제하는 것으로 즉시 반영할 수 있습니다.
        </p>
      </section>
    </div>
  );
}
