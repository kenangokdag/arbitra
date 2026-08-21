export type MockProject = {
  id: string;
  name: string;
  description: string;
  lastActivity: string;
  paperCount: number;
  status: string;
  color: string;
};

export type MockPaper = {
  id: string;
  title: string;
  authors: string;
  journal: string;
  year: number;
  citations: number;
  estra: { d: number; w: number; s: number; t: number };
  confidence: number;
  method: string;
  quartile: string;
  openAccess: boolean;
  abstract: string;
};

export const MOCK_PROJECTS: MockProject[] = [
  {
    id: "p1",
    name: "MCDM ve Akreditasyon",
    description: "Cok kriterli karar verme yontemlerinin yuksekogretim akreditasyonunda kullanimi",
    lastActivity: "2 saat once",
    paperCount: 47,
    status: "active",
    color: "#4F46E5",
  },
  {
    id: "p2",
    name: "Ortaokul Matematik Kaygisi",
    description: "Turkiye'de ortaokul ogrencilerinde matematik kaygisi nedenleri ve mudahaleler",
    lastActivity: "Dun",
    paperCount: 23,
    status: "active",
    color: "#7C3AED",
  },
  {
    id: "p3",
    name: "Online Egitim Etkinligi",
    description: "Pandemi sonrasi online egitim modellerinin etkinlik karsilastirmasi",
    lastActivity: "3 gun once",
    paperCount: 64,
    status: "active",
    color: "#D97706",
  },
];

export const MOCK_PAPERS: MockPaper[] = [
  {
    id: "a1",
    title: "Multi-Criteria Decision Making in Higher Education Accreditation: A Turkish Case Study",
    authors: "Yilmaz, A., Kara, B., ve 3 diger",
    journal: "Studies in Higher Education",
    year: 2024,
    citations: 47,
    estra: { d: 88, w: 75, s: 92, t: 81 },
    confidence: 85,
    method: "Nicel",
    quartile: "Q1",
    openAccess: true,
    abstract:
      "This study explores the application of multi-criteria decision making (MCDM) frameworks within the context of Turkish higher education accreditation processes, focusing on how institutional quality is measured and benchmarked.",
  },
  {
    id: "a2",
    title: "AHP-TOPSIS Hybrid Approach for University Quality Assessment",
    authors: "Demir, M., Sahin, K., ve 2 diger",
    journal: "European Journal of Education",
    year: 2023,
    citations: 124,
    estra: { d: 92, w: 88, s: 79, t: 85 },
    confidence: 91,
    method: "Meta-analiz",
    quartile: "Q1",
    openAccess: false,
    abstract:
      "We propose a hybrid AHP-TOPSIS approach to evaluate university quality across multiple dimensions, validated through case studies from 12 institutions across Europe and Turkiye.",
  },
  {
    id: "a3",
    title: "Stakeholder Perspectives on Accreditation Criteria",
    authors: "Aydin, F., Celik, R.",
    journal: "Quality in Higher Education",
    year: 2024,
    citations: 18,
    estra: { d: 65, w: 71, s: 68, t: 72 },
    confidence: 58,
    method: "Nitel",
    quartile: "Q2",
    openAccess: true,
    abstract:
      "Through semi-structured interviews with 34 stakeholders, this paper examines diverging perspectives on what constitutes meaningful accreditation criteria.",
  },
  {
    id: "a4",
    title: "ENTROPY-VIKOR Method for Educational Quality Indicators",
    authors: "Ozturk, S., Polat, H., ve 4 diger",
    journal: "Computers & Education",
    year: 2023,
    citations: 89,
    estra: { d: 81, w: 85, s: 88, t: 79 },
    confidence: 78,
    method: "Nicel",
    quartile: "Q1",
    openAccess: true,
    abstract:
      "This paper introduces an ENTROPY-VIKOR hybrid method specifically calibrated for educational quality indicators in K-12 and higher education contexts.",
  },
];
