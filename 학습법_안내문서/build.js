const fs=require('fs');
const D=require('docx');
const {Document,Packer,Paragraph,TextRun,Table,TableRow,TableCell,ImageRun,WidthType,ShadingType,BorderStyle,AlignmentType,HeadingLevel,TableOfContents,PageBreak,LevelFormat,Footer,PageNumber}=D;
const BODY='ChangwonDangamRound', HEAD='ChangwonDangamAsac Bold';
const BEIGE='E8E8DF', W=9638; // A4 w/ 1.5cm... content width DXA
const run=(t,o={})=>new TextRun({text:t,font:BODY,size:22,...o});
const P=(c,o={})=>new Paragraph({spacing:{after:120,line:360},...o,children:Array.isArray(c)?c:[run(c)]});
const H1=t=>new Paragraph({heading:HeadingLevel.HEADING_1,spacing:{before:300,after:140},border:{bottom:{style:BorderStyle.SINGLE,size:8,color:'000000',space:2}},children:[new TextRun({text:t,font:HEAD,size:34,bold:false})]});
const H2=t=>new Paragraph({heading:HeadingLevel.HEADING_2,spacing:{before:180,after:80},children:[new TextRun({text:t,font:HEAD,size:28})]});
const B=(c)=>new Paragraph({numbering:{reference:'b',level:0},spacing:{after:80,line:340},children:Array.isArray(c)?c:[run(c)]});
const bd={style:BorderStyle.SINGLE,size:4,color:'000000'}; const borders={top:bd,bottom:bd,left:bd,right:bd};
const cell=(t,w,{head=false,fill}={})=>new TableCell({width:{size:w,type:WidthType.DXA},borders,margins:{top:80,bottom:80,left:110,right:110},
  shading:{type:ShadingType.CLEAR,fill:fill||(head?BEIGE:'FFFFFF'),color:'auto'},
  children:(Array.isArray(t)?t:[t]).map(x=>new Paragraph({spacing:{after:40,line:320},children:[run(x,head?{font:HEAD,size:22}:{size:22})]}))});
const table=(widths,rows)=>new Table({width:{size:widths.reduce((a,b)=>a+b),type:WidthType.DXA},columnWidths:widths,
  rows:rows.map((r,i)=>new TableRow({tableHeader:i==0,cantSplit:true,children:r.map((t,j)=>cell(t,widths[j],{head:i==0||false,fill:(i>0&&j==0)?'F4F4EE':undefined}))}))});
const box=(title,lines)=>new Table({width:{size:W,type:WidthType.DXA},columnWidths:[W],rows:[new TableRow({children:[new TableCell({width:{size:W,type:WidthType.DXA},borders,shading:{type:ShadingType.CLEAR,fill:BEIGE,color:'auto'},margins:{top:120,bottom:120,left:200,right:200},
  children:[new Paragraph({spacing:{after:80},children:[new TextRun({text:title,font:HEAD,size:26})]}),...lines.map(l=>new Paragraph({spacing:{after:60,line:330},children:Array.isArray(l)?l:[run(l,{size:22})]}))]})]})]});
const sp=()=>new Paragraph({spacing:{after:120},children:[]});
const img=(f,w,h,t)=>new ImageRun({type:f.endsWith('png')?'png':'jpg',data:fs.readFileSync(f),transformation:{width:w,height:h},altText:{title:t,description:t,name:t}});
const C=(c)=>new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:80},children:c});
const cap=t=>new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:160},children:[run(t,{size:20})]});
const band=(t,o)=>new Paragraph({shading:{type:ShadingType.CLEAR,fill:BEIGE},indent:{left:200,right:200},spacing:{after:0},children:[new TextRun({text:t,...o})]});
const tocBox=new Table({width:{size:W,type:WidthType.DXA},columnWidths:[W],rows:[new TableRow({children:[new TableCell({width:{size:W,type:WidthType.DXA},borders,margins:{top:120,bottom:120,left:200,right:200},
  children:[new Paragraph({spacing:{after:80},children:[new TextRun({text:'목차',font:HEAD,size:28})]}),new TableOfContents('목차',{hyperlink:true,headingStyleRange:'1-1'})]})]})]});

const cover=[
 band(' ',{size:40}),
 band('중학교 1학년을 위한 공부 안내',{font:BODY,size:28}),
 band('공부, 어떻게 확인할까요?',{font:HEAD,size:64}),
 new Paragraph({shading:{type:ShadingType.CLEAR,fill:BEIGE},indent:{left:200,right:200},spacing:{after:240},children:[new TextRun({text:'평가를 내 공부에 쓰는 방법',font:BODY,size:30})]}),
 tocBox, sp(),
];

const body=[
H1('1. 평가는 왜 필요할까요?'),
P('평가는 "점수를 매기는 일"만이 아니에요. 내가 얼마나 알고 있는지 확인하고, 부족한 부분을 찾아 고치게 도와주는 일이에요. 선생님도 평가 결과를 보고 우리를 어떻게 도울지 정해요.'),
B('지금 내 실력을 알 수 있어요.'),
B('틀린 곳을 찾아 다시 공부할 수 있어요.'),
B('시험 전에 무엇을 먼저 봐야 할지 알 수 있어요.'),

H1('2. 평가 3가지'),
P('평가는 하는 때에 따라 세 가지로 나눠요. 이름을 알아 두면 공부 계획을 세우기 쉬워요.'),
table([1500,2000,2700,3438],[
 ['이름','하는 때','하는 일','내 공부에 쓰는 방법'],
 ['진단평가','공부를 시작하기 전','내가 이미 아는 것과 모르는 것을 알아봐요.','내 수준을 알고 공부 계획을 짜요.'],
 ['형성평가','공부하는 중간','배운 것을 잘 이해했는지 확인해요.','틀린 곳을 바로 고치고 집중해서 공부해요.'],
 ['총괄평가','단원이나 학기가 끝난 뒤','마지막으로 얼마나 익혔는지 알아봐요. (중간·기말고사)','빠진 부분을 채울 계획을 세우고 내 공부 태도를 살펴요.'],
]),sp(),

H1('3. 내 노트 만들기 (수업 중)'),
P('좋은 평가 공부는 좋은 노트에서 시작해요. 수업을 들으면서 바로 만드는 노트예요.'),
B('선생님 말씀을 들으면서 바로 짧게 줄여서 적어요.'),
B([run('단원이 바뀔 때마다 단원 포스트잇을 붙여요. '),run('(꼭 해야 해요)',{bold:true})]),
B([run('중요한 정도에 따라 펜 색을 달리해요. '),run('(꼭 해야 해요)',{bold:true})]),
sp(),
table([2400,2400,4838],[
 ['중요한 정도','쓰는 도구','이럴 때 써요'],
 ['가장 중요','🔴 빨간 펜','꼭 외울 것'],
 ['두 번째','🔵 파란 펜','중요한 설명'],
 ['세 번째','⚫ 검은 펜','일반 필기'],
 ['네 번째','✏️ 연필','덧붙인 생각, 참고 내용'],
]),sp(),
P([run('중요한 정도는 이렇게 정해요. 아래에 많이 해당할수록 더 중요해요.',{bold:true})]),
B('시험에 자주 나온 것 (기출 문제)'),
B('선생님이 같은 말을 여러 번 반복한 것'),
B('학습 목표에 같은 낱말이 들어 있는 것'),
B('다른 문제집에서도 되풀이해서 설명하는 것'),

H1('4. 평가별 공부 방법'),
P('아래 순서대로 하면 틀린 곳이 점점 줄어들어요.'),
H2('① 진단평가: 공부를 시작하기 전'),
P('지금 내 수준을 알아서 공부 계획을 짜는 데 써요. 이렇게 알아봐요.'),
B('공부할 순서를 정해요.'),
B('이전에 배운 것 중 더 공부해야 할 것을 찾아요.'),
B('앞으로 배울 내용 중 내가 더 봐야 할 부분을 미리 알아 둬요.'),
P('단원 제목을 보고 "아는 것"과 "모르는 것"을 나눠 적어 보세요. 모르는 것을 중심으로 수업을 들어요.'),
H2('② 형성평가: 수업이 끝난 뒤'),
P('중요한 것부터 짧은 문제(단답형)를 풀어요. 틀린 곳은 바로 고치고, 그 부분을 집중해서 다시 공부해요.'),
B('틀린 내용은 노트에서 노란 형광펜으로 표시해요.'),
B('형광펜 부분에는 노란색 작은 포스트잇을 붙여요. 단원 포스트잇과 달라야 해요.'),
P('바로 고친 경험은 "내가 해냈다"는 만족감을 주고, 공부하고 싶은 마음을 키워 줘요. 그래도 마음이 잘 안 생기면 스스로에게 상을 주거나, 부모님과 약속을 정해서 선물 같은 보상을 받아요.'),
H2('③ 형성평가: 단원이 끝난 뒤'),
P('같은 내용을 짧은 문제(단답형)로 한 번 더 풀어요.'),
B('새로 틀린 내용 → 노란 형광펜 + 노란 포스트잇'),
B('이미 노란 형광펜이 있는데 또 틀린 내용 → 빨간 별 + 분홍 포스트잇'),
H2('④ 총괄평가 준비: 시험 1주일 전'),
P('실제 시험처럼 시간을 정해 놓고 문제를 풀어요. 틀린 내용은 별 두 개(★★)와 초록 포스트잇으로 표시해요.'),
P('결과를 보면서 내 공부 태도도 살펴봐요.'),
B('앞에서 빠뜨린 부분이 없는지 확인해요.'),
B('빠진 부분을 채울 계획을 "무엇을, 언제, 얼마나" 하는지 행동으로 써요. (예: "화요일 저녁에 3단원 표시한 곳 5개 다시 쓰기") 구체적으로 쓰면 실제로 하게 돼요.'),
B('내 공부 태도를 돌아보고, 앞으로도 계속할 공부 습관을 만들어요.'),
H2('⑤ 시험 당일: 쉬는 시간'),
P('새로 공부하지 말고, 노트에서 형광펜과 별 표시가 있는 곳만 빠르게 읽어 봐요.'),
sp(),
table([2700,3200,3738],[
 ['상황','표시','포스트잇'],
 ['단원이 시작될 때','제목을 크게 적기','단원 포스트잇 (큰 것)'],
 ['처음 틀림','노란 형광펜','노란색 작은 포스트잇'],
 ['또 틀림','빨간 별','분홍색 포스트잇'],
 ['시험 직전 모의 풀이에서 틀림','별 두 개 (★★)','초록색 포스트잇'],
]),sp(),

H1('5. 필기·요약 요령'),
B('말을 그대로 받아 적지 않고, 중요한 낱말만 골라 적어요.'),
B('줄을 나누고 화살표(→)로 이어서 서로 어떤 관계인지 보이게 해요.'),
B('긴 내용은 번호를 붙여 정리해요. 번호는 이 순서로 써요.'),
P([run('1.  →  1)  →  (1)  →  ①  →  가.  →  가)  →  (가)  →  ㉮',{size:24,bold:true})],{alignment:AlignmentType.CENTER}),
B('코넬 노트(칸 나누기 노트)는 해도 되고 안 해도 돼요. 하고 싶을 때만 써요.'),
P('코넬 노트는 종이를 네 칸으로 나눠요. 위쪽은 제목, 왼쪽은 중요한 낱말(키워드), 오른쪽은 수업 필기, 아래쪽은 배운 내용을 한두 줄로 줄인 요약을 써요.'),
C([img('코넬노트.png',230,343,'코넬 노트 칸 나누기')]),
cap('▲ 코넬 노트 칸 나누기: 제목 / 키워드 / 노트필기 / 요약 영역'),

H1('6. 심화: 한 장 정리본'),
P('노트 정리와 한 장 정리본은 쓰임이 달라요. 중1 시험에는 보통 노트 정리가 알맞고, 한 장 정리본은 넓은 범위를 볼 때 도전해 봐요.'),
table([1800,3919,3919],[
 ['','노트 정리','한 장 정리본'],
 ['알맞은 때','중간·기말고사, 외울 것이 많은 과목, 양이 적은 공부','수능처럼 한 과목 전체를 한 번에 볼 때'],
 ['방법','수업 때 요약해 적고 단원별로 표시','큰 종이(A3) 한 장에 배운 내용을 모두 정리'],
 ['특징','틀린 곳을 표시하며 계속 고쳐요','칸을 접어 단원별로 나누고, 관련된 내용은 선으로 이어요'],
]),sp(),
P('색 규칙: 빨강=가장 중요한 것 / 초록+Q=이미 시험에 나온 문제 / 파랑=덧붙인 설명 / 연한 검정 선=관련된 내용 잇기'),
C([img('한장정리본.jpg',480,360,'한 장 정리본 예시')]),
cap('▲ 한 장 정리본 예시 (칸을 나누고 색과 선으로 정리)'),

H1('7. 한꺼번에 보기'),
table([2300,5338,2000],[
 ['때','할 일','확인'],
 ['수업 시간','요약 필기 + 단원 포스트잇 + 중요도 펜','☐'],
 ['수업 직후','짧은 문제(단답형) → 틀린 곳 노란 형광펜 + 노란 포스트잇','☐'],
 ['단원이 끝난 뒤','다시 풀기 → 새로 틀림은 노란 형광펜, 또 틀림은 빨간 별 + 분홍 포스트잇','☐'],
 ['시험 1주일 전','시간을 정해 모의 풀이 → 틀린 곳 ★★ + 초록 포스트잇, 보완 계획 쓰기','☐'],
 ['시험 당일 쉬는 시간','형광펜·별 표시만 빠르게 읽기','☐'],
]),sp(),

H1('참고 자료: 예시 사진'),
box('예시 사진 안내',[
 [run('아래 노트 사진은 위 방법 중 ',{size:22}),run('일부만',{size:22,bold:true}),run(' 적용한 예시예요.',{size:22})],
 [run('사진에 적용된 것: ',{size:22,bold:true}),run('요약해서 적은 필기 / 회색 형광펜으로 제목 구분 / 형광펜으로 처음 틀린 곳 표시 (사진은 빨강 계열 형광펜, 이 문서는 노란색 기준) / 빨간 별로 또 틀린 곳 표시',{size:22})],
 [run('사진에 없는 것: ',{size:22,bold:true}),run('포스트잇, 중요도 펜 색 나누기',{size:22})],
 [run('사진에 없어도 포스트잇과 중요도 표시는 반드시 해야 해요!',{size:22,bold:true})],
]),sp(),
C([img('노트예시.jpg',300,379,'노트 예시')]),
cap('▲ 요약해서 적은 노트 예시'),
P([run('※ 교육부 자료, 학술 논문, 합격 수기를 참고해 중1 눈높이로 쉽게 풀어 썼어요.',{size:18})],{spacing:{before:200}}),
];

const doc=new Document({
 fonts:[{name:BODY,data:fs.readFileSync('fonts/ChangwonDangamRound.ttf'),characterSet:'81'},{name:HEAD,data:fs.readFileSync('fonts/ChangwonDangamAsac-Bold.ttf'),characterSet:'81'}],
 features:{updateFields:true},
 styles:{default:{document:{run:{font:BODY,size:24}}},
  paragraphStyles:[{id:'Heading1',name:'Heading 1',basedOn:'Normal',next:'Normal',quickFormat:true,run:{font:HEAD,size:34},paragraph:{outlineLevel:0}},
  {id:'Heading2',name:'Heading 2',basedOn:'Normal',next:'Normal',quickFormat:true,run:{font:HEAD,size:28},paragraph:{outlineLevel:1}}]},
 numbering:{config:[{reference:'b',levels:[{level:0,format:LevelFormat.BULLET,text:'•',alignment:AlignmentType.LEFT,style:{paragraph:{indent:{left:560,hanging:280}}}}]}]},
 sections:[{properties:{page:{size:{width:11906,height:16838},margin:{top:1134,bottom:1134,left:1134,right:1134}}},
  footers:{default:new Footer({children:[new Paragraph({alignment:AlignmentType.CENTER,children:[new TextRun({children:[PageNumber.CURRENT],font:BODY,size:20})]})]})},
  children:[...cover,...body]}]});
Packer.toBuffer(doc).then(b=>{fs.writeFileSync('공부방법_안내문.docx',b);console.log('ok')});
