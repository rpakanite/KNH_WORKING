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

const cover=[
 new Paragraph({spacing:{before:600,after:0},shading:{type:ShadingType.CLEAR,fill:BEIGE},indent:{left:200,right:200},children:[new TextRun({text:' ',size:40})]}),
 new Paragraph({shading:{type:ShadingType.CLEAR,fill:BEIGE},indent:{left:200,right:200},children:[new TextRun({text:'중학교 1학년을 위한 공부 안내',font:BODY,size:28})]}),
 new Paragraph({shading:{type:ShadingType.CLEAR,fill:BEIGE},indent:{left:200,right:200},spacing:{after:0},children:[new TextRun({text:'공부, 어떻게 확인할까요?',font:HEAD,size:64})]}),
 new Paragraph({shading:{type:ShadingType.CLEAR,fill:BEIGE},indent:{left:200,right:200},spacing:{after:300},children:[new TextRun({text:'평가를 내 공부에 쓰는 방법',font:BODY,size:30})]}),
 new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:80},children:[new ImageRun({type:'jpg',data:fs.readFileSync('노트예시.jpg'),transformation:{width:340,height:429},altText:{title:'노트 예시',description:'요약 필기 노트 예시',name:'note'}})]}),
 new Paragraph({alignment:AlignmentType.CENTER,spacing:{after:200},children:[run('▲ 요약해서 적은 노트 예시 (자세한 설명은 4번)',{size:20})]}),
 new Paragraph({children:[new PageBreak()]}),
 new Paragraph({spacing:{after:160},children:[new TextRun({text:'목차',font:HEAD,size:40})]}),
 new TableOfContents('목차',{hyperlink:true,headingStyleRange:'1-1'}),
 new Paragraph({children:[new PageBreak()]}),
];

const body=[
H1('1. 평가는 왜 필요할까요?'),
P('평가는 "점수를 매기는 일"만이 아니에요. 내가 얼마나 알고 있는지 확인하고, 부족한 부분을 찾아 고치게 도와주는 일이에요. 선생님도 평가 결과를 보고 우리를 어떻게 도울지 정해요.'),
B([run('지금 내 실력을 알 수 있어요.')]),
B([run('틀린 곳을 찾아 다시 공부할 수 있어요.')]),
B([run('시험 전에 무엇을 먼저 봐야 할지 알 수 있어요.')]),

H1('2. 평가 3가지'),
P('평가는 하는 때에 따라 세 가지로 나눠요. 이름을 알아 두면 공부 계획을 세우기 쉬워요.'),
table([1500,2100,2800,3238],[
 ['이름','하는 때','하는 일','내 공부에 쓰는 방법'],
 ['진단평가','공부를 시작하기 전','내가 이미 아는 것과 모르는 것을 알아봐요.','모르는 부분에 더 시간을 써요.'],
 ['형성평가','공부하는 중간','배운 것을 잘 이해했는지 확인해요.','틀린 곳을 바로 고쳐요.'],
 ['총괄평가','단원이나 학기가 끝난 뒤','마지막으로 얼마나 익혔는지 알아봐요. (중간·기말고사)','결과를 보고 다음 공부 계획을 세워요.'],
]),sp(),

H1('3. 내 노트 만들기 (수업 중)'),
P('좋은 평가 공부는 좋은 노트에서 시작해요. 수업을 들으면서 바로 만드는 노트예요.'),
B([run('선생님 말씀을 들으면서 바로 짧게 줄여서 적어요.')]),
B([run('단원이 바뀔 때마다 단원 포스트잇을 붙여요. ',{}),run('(꼭 해야 해요)',{bold:true})]),
B([run('중요한 정도에 따라 펜 색을 달리해요. ',{}),run('(꼭 해야 해요)',{bold:true})]),
sp(),
table([2000,2200,5438],[
 ['중요한 정도','쓰는 도구','이럴 때 써요'],
 ['가장 중요','빨간 펜','꼭 외울 것'],
 ['두 번째','파란 펜','중요한 설명'],
 ['세 번째','검은 펜','일반 필기'],
 ['네 번째','연필','덧붙인 생각, 참고 내용'],
]),sp(),

H1('4. 평가별 공부 방법'),
P('아래 순서대로 하면 틀린 곳이 점점 줄어들어요.'),
H2('① 진단: 공부를 시작하기 전'),
P('단원 제목을 보고 "내가 아는 것"과 "모르는 것"을 나눠 적어 봐요. 모르는 것을 중심으로 수업을 들어요.'),
H2('② 형성평가: 수업이 끝난 뒤'),
P('중요한 것부터 짧은 문제(단답형)를 풀어요. (예: "형성평가란 무엇인가요?" → 한두 줄로 써요.)'),
B([run('틀린 내용은 노트에서 노란 형광펜으로 표시해요.')]),
B([run('형광펜 부분에는 작은 포스트잇을 붙여요. 단원 포스트잇과 모양이나 색이 달라야 해요.')]),
H2('③ 형성평가: 단원이 끝난 뒤'),
P('같은 내용을 짧은 문제(단답형)로 한 번 더 풀어요.'),
B([run('새로 틀린 내용 → 노란 형광펜 + 작은 포스트잇')]),
B([run('이미 노란 형광펜이 있는데 또 틀린 내용 → 빨간 별 + 포스트잇')]),
H2('④ 총괄평가 준비: 시험 1주일 전'),
P('실제 시험처럼 시간을 정해 놓고 문제를 풀어요. 틀린 내용은 위와 같은 방법으로 표시해요.'),
H2('⑤ 시험 당일: 쉬는 시간'),
P('새로 공부하지 말고, 노트에서 형광펜과 별 표시가 있는 곳만 빠르게 읽어 봐요.'),
sp(),
table([2300,3300,4038],[
 ['상황','표시','포스트잇'],
 ['단원이 시작될 때','제목을 크게 적기','단원 포스트잇 (큰 것)'],
 ['처음 틀림','노란 형광펜','작은 포스트잇 (단원용과 구분)'],
 ['또 틀림','빨간 별','포스트잇'],
 ['시험 직전 모의 풀이에서 틀림','위와 같은 방법','위와 같은 방법'],
]),sp(),
box('예시 사진 안내',[
 [run('표지의 노트 사진은 위 방법 중 ',{size:22}),run('일부만',{size:22,bold:true}),run(' 적용한 예시예요.',{size:22})],
 [run('사진에 적용된 것: ',{size:22,bold:true}),run('요약해서 적은 필기 / 회색 형광펜으로 제목 구분 / 형광펜으로 처음 틀린 곳 표시 (사진은 빨강 계열 형광펜, 이 문서는 노란색 기준) / 빨간 별로 또 틀린 곳 표시',{size:22})],
 [run('사진에 없는 것: ',{size:22,bold:true}),run('포스트잇, 중요도 펜 색 나누기',{size:22})],
 [run('사진에 없어도 포스트잇과 중요도 표시는 반드시 해야 해요!',{size:22,bold:true})],
]),sp(),

H1('5. 필기·요약 요령'),
B([run('말을 그대로 받아 적지 않고, 중요한 낱말만 골라 적어요.')]),
B([run('줄을 나누고 화살표(→)로 이어서 서로 어떤 관계인지 보이게 해요.')]),
B([run('긴 내용은 "가, 나, 다"처럼 번호를 붙여 줄여요.')]),
B([run('칸 나누기 노트(코넬 노트): 종이를 나눠 왼쪽엔 중요한 낱말, 오른쪽엔 설명, 맨 아래엔 한 줄 요약을 써요.')]),
B([run('외울 때는 읽기만 하지 말고, 가리고 떠올려서 직접 써 봐요. 떠올려 쓸수록 오래 기억돼요.')]),

H1('6. 심화: 한 장 정리본'),
P('노트 정리와 한 장 정리본은 쓰임이 달라요. 중1 시험에는 보통 노트 정리가 알맞고, 한 장 정리본은 넓은 범위를 볼 때 도전해 봐요.'),
table([1800,3919,3919],[
 ['','노트 정리','한 장 정리본'],
 ['알맞은 때','중간·기말고사, 외울 것이 많은 과목, 양이 적은 공부','수능처럼 한 과목 전체를 한 번에 볼 때'],
 ['방법','수업 때 요약해 적고 단원별로 표시','큰 종이(A3) 한 장에 배운 내용을 모두 정리'],
 ['특징','틀린 곳을 표시하며 계속 고쳐요','칸을 접어 단원별로 나누고, 관련된 내용은 선으로 이어요'],
]),sp(),
P('색 규칙: 빨강=가장 중요한 것 / 초록+Q=이미 시험에 나온 문제 / 파랑=덧붙인 설명 / 연한 검정 선=관련된 내용 잇기'),

H1('7. 한꺼번에 보기'),
table([2300,5338,2000],[
 ['때','할 일','확인'],
 ['수업 시간','요약 필기 + 단원 포스트잇 + 중요도 펜','☐'],
 ['수업 직후','짧은 문제(단답형) → 틀린 곳 노란 형광펜 + 작은 포스트잇','☐'],
 ['단원이 끝난 뒤','다시 풀기 → 새로 틀림은 노란 형광펜, 또 틀림은 빨간 별','☐'],
 ['시험 1주일 전','시간을 정해 모의 풀이 → 틀린 곳 표시','☐'],
 ['시험 당일 쉬는 시간','형광펜·별 표시만 빠르게 읽기','☐'],
]),sp(),
box('쉬운 말 풀이',[
 '평가: 내가 얼마나 아는지 확인하는 일',
 '복습: 배운 것을 다시 공부하는 것',
 '내용: 배우는 것 하나하나',
 '단답형: 짧게 한두 줄로 답하는 문제 (학교에서는 "서답형"이라고도 해요)',
 '형광펜: 글 위에 색을 칠해 잘 보이게 하는 펜',
 '틀린 문제: 답을 잘못 쓴 문제',
 '기출: 이미 시험에 나온 적이 있는 문제',
]),
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
