// Central content module. All asset paths are absolute (served from /assets at
// the GitHub Pages root). Filenames preserve EXACT casing because the CI build
// runs on a case-sensitive Linux filesystem. Spaces in filenames are encoded.

export type Photo = {
  thumb: string;
  full: string;
  caption?: string;
};

export type VideoItem = {
  id: string;
  title: string;
  quality: string;
  year: string;
  description: string;
  youtubeId: string;
};

export type Sport = {
  emoji: string;
  name: string;
  since: string;
  description: string;
  images: string[];
};

export type Hobby = {
  emoji: string;
  name: string;
  description: string;
};

export type Essay = {
  title: string;
  pdf: string;
  abstract: string;
  figures: { src: string; alt: string; width: string }[];
};

const pic = (name: string) => `/assets/pictures/${encodeURI(name)}`;
const thumb = (name: string) => `/assets/thumbnails/${encodeURI(name)}`;
const pdf = (name: string) => `/assets/pdf/${encodeURI(name)}`;

export const bio = {
  name: "James Sui",
  tagline: "Tech, Motion, and Perspective.",
  role: "Student · Photographer · Athlete · Technologist",
  location: "Shanghai, China",
  age: 17,
  email: "suihe0812@gmail.com",
  profileImage: thumb("IMG_6679.jpg"),
  paragraphs: [
    "Hi! I'm a 17-year-old student living in Shanghai. I'm passionate about technology, and I enjoy spending my time exploring a mix of digital and real-world interests.",
    "I love gaming, especially FPS titles like Apex Legends and Overwatch. Outside of gaming, I'm heavily involved in sports such as ice hockey, tennis, and floorball. You'll also probably find me enjoying ice cream or anything apple-flavored—juice, pie, you name it.",
  ],
};

export const heroImage = pic("2-4jpn (17 - 37).jpg");
export const heroCaption =
  "Japan, Hokkaido — a solitary evergreen, lit from below against the snow.";

export const socials: { label: string; href: string; kind: "email" | "youtube" }[] =
  [
    { label: "Email", href: "mailto:suihe0812@gmail.com", kind: "email" },
    {
      label: "YouTube",
      href: "https://www.youtube.com/@cheezecats",
      kind: "youtube",
    },
  ];

const photo = (thumbName: string, fullName: string, caption?: string): Photo => ({
  thumb: thumb(thumbName),
  full: pic(fullName),
  caption,
});

export const photos: Photo[] = [
  photo("3T6A3836.jpg", "3T6A3836.jpg", "Italy, Toscany at sunset — capturing the black and orange tones."),
  photo("_T6A2660.jpg", "_T6A2660.JPG"),
  photo("_T6A2724.jpg", "_T6A2724.jpg"),
  photo("_T6A3351.jpg", "_T6A3351.jpg"),
  photo("_T6A3526.jpg", "_T6A3526.jpg"),
  photo("DSC_0348.jpg", "DSC_0348.jpg"),
  photo("_T6A3542.jpg", "_T6A3542.jpg"),
  photo("_T6A3720.jpg", "_T6A3720.jpg"),
  photo("_T6A6000.jpg", "_T6A6000.jpg"),
  photo("_T6A5346.jpg", "_T6A5346.jpg"),
  photo("_T6A5411.jpg", "_T6A5411.jpg"),
  photo("_T6A6182.jpg", "_T6A6182.jpg"),
  photo("DSC_0187.jpg", "DSC_0187.jpg"),
  photo("3T6A3960.jpg", "3T6A3960.jpg"),
  photo("_T6A6134.jpg", "_T6A6134.jpg"),
  photo("DSC_0046.jpg", "DSC_0046.jpg"),
  photo("DSC_0438.jpg", "DSC_0438.jpg"),
  photo("2-4jpn (1 - 37).jpg", "2-4jpn (1 - 37).jpg"),
  photo("2-4jpn (2 - 37).jpg", "2-4jpn (2 - 37).jpg"),
  photo("2-4jpn (3 - 37).jpg", "2-4jpn (3 - 37).jpg"),
  photo("IMG_8240.jpg", "IMG_8240.jpg"),
  photo("2-4jpn (17 - 37).jpg", "2-4jpn (17 - 37).jpg", "Japan, Hokkaido — night shot of a solitary evergreen tree illuminated from below, surrounded by snow."),
  photo("2-4jpn (25 - 37).jpg", "2-4jpn (25 - 37).jpg"),
  photo("2-4jpn (26 - 37).jpg", "2-4jpn (26 - 37).jpg"),
  photo("2-4jpn (29 - 37).jpg", "2-4jpn (29 - 37).jpg"),
  photo("2-4jpn (35 - 37).jpg", "2-4jpn (35 - 37).jpg"),
  photo("2-4jpn (7 - 37).jpg", "2-4jpn (7 - 37).jpg"),
  photo("2-4jpn (8 - 37).jpg", "2-4jpn (8 - 37).jpg"),
  photo("_T6A5313.jpg", "_T6A5313.jpg"),
  photo("_T6A6070.jpg", "_T6A6070.jpg"),
  photo("_T6A6328.jpg", "_T6A6328.jpg"),
  photo("DSC_0480.jpg", "DSC_0480.jpg", "Greece, Athens — view of the National Observatory of Athens nestled among lush greenery under a soft, fading twilight sky."),
  photo("IMG_7739.jpg", "IMG_7739.jpg"),
  photo("2-4jpn (16 - 37).jpg", "2-4jpn (16 - 37).jpg", "Japan, Hokkaido — a 7-Eleven storefront glows against the dark, snow-covered landscape of a winter night."),
];

export const videos: VideoItem[] = [
  {
    id: "greece-8k",
    title: "Greece",
    quality: "8K",
    year: "2024",
    youtubeId: "RUg2hiRTRVM",
    description:
      "Filmed 2024, captured 8K on the Nikon Z8. Exploring my experience of Greece, including the ancient marble of Athens and the deep turquoise waters of the Ionian Sea.",
  },
  {
    id: "japan-winter-4k",
    title: "Japan Winter",
    quality: "4K",
    year: "2025",
    youtubeId: "r7WEc5foYU8",
    description:
      "Filmed 2025, captured 4K on the Nikon Z8. Exploring the quiet beauty of a Japanese winter, from the snow-heavy forests of Hokkaido to the frozen shrines of the north.",
  },
  {
    id: "japan-vlog-4k",
    title: "Japan Vlog",
    quality: "4K",
    year: "2024",
    youtubeId: "myZ1VWSJMZw",
    description:
      "Filmed 2024, captured 4K. A more personal look at life in Japan, wandering through the neon lights of Tokyo and the hidden side streets of Kyoto.",
  },
];

export const sports: Sport[] = [
  {
    emoji: "⛷️",
    name: "Skiing",
    since: "2013",
    description:
      "Skiing and snowboarding is a winter passion that I look forward to every year and also an important family tradition. The thrill of gliding down snowy slopes and the serene beauty of winter landscapes never fail to captivate me. From carving turns on groomed trails to exploring powder-filled backcountry, and park riding, skiing always keeps me excited and challenged.",
    images: [pic("IMG_0498.JPG"), pic("IMG_0672.jpg"), pic("IMG_1236.jpg")],
  },
  {
    emoji: "🏒",
    name: "Ice Hockey",
    since: "2015",
    description:
      "My journey with ice hockey began at a young age. The speed, strategy, and teamwork required in this sport excites me every time I play. I have been actively involved in local leagues and have participated in numerous training sessions both abroad (America, Japan, Russia) and domestically.",
    images: [pic("IMG_6993.JPG"), pic("IMG_8937.JPG")],
  },
  {
    emoji: "🎾",
    name: "Tennis",
    since: "2018",
    description:
      "Tennis started as a sport I can play in my community with my friends and family. Moving forwards, other than practising every week, I started to attend local tournaments to improve my skill. The individual nature of tennis is both challenging and rewarding — a completely different experience from team sports.",
    images: [pic("IMG_2046.jpg"), pic("微信图片_20260110220212_12_136.jpg")],
  },
  {
    emoji: "🥍",
    name: "Floorball",
    since: "2023",
    description:
      "Floorball brought a fresh perspective to my sporting life when I joined my school's varsity team. I originally saw it as a way to keep my hockey skills sharp during boarding, but I soon found myself captivated by the game's distinct flow. Transitioning from the ice to the court required a quick study of new mechanics, and I've loved every bit of the learning curve.",
    images: [
      pic("498a3dc4b68680a868b211bd4f37e237.JPG"),
      pic("5bc1d4d1f7a92501a2d9fb6607ca2339.JPG"),
    ],
  },
];

export const otherHobbies: Hobby[] = [
  {
    emoji: "🎮",
    name: "Gaming",
    description:
      "Video games have always been my favorite way to unwind and decompress after school. My interests span a wide variety of genres: from high-stakes shooters like Apex Legends and Counter-Strike to the strategic depth of Civilization. Whether I'm immersing myself in the world of Cyberpunk 2077 or enjoying a round of Mario Kart with friends, gaming provides a diverse range of experiences that help me relax and stay connected.",
  },
  {
    emoji: "🎸",
    name: "Electric Guitar",
    description:
      "About a year ago, I picked up the electric guitar to explore my passion for music, specifically within the J-pop and rock genres. As a self-taught musician, I've navigated the learning process through online tutorials and by playing along to my favorite tracks.",
  },
];

export const essays: Essay[] = [
  {
    title: "Hallucinations in Large Language Models",
    pdf: pdf("essay llm.pdf"),
    abstract:
      "This study investigates hallucinations in large language models, examining why they occur and how they relate to model size. Using Gemma-3 models and the SimpleQA benchmark, it shows that scaling parameters alone is insufficient, highlighting the need for architectural improvements and stronger mitigation strategies.",
    figures: [
      { src: pdf("table_his.png"), alt: "Hallucination results table", width: "70%" },
      { src: pdf("table_his2.png"), alt: "Additional hallucination results table", width: "70%" },
    ],
  },
  {
    title: "Benchmarking Neural Classifiers for Medical Imaging",
    pdf: pdf("essay his.pdf"),
    abstract:
      "This paper benchmarks multiple classifier architectures for medical image classification using histology embeddings. Comparing attention pooling, KNN, and MLP models, it evaluates accuracy, efficiency, and robustness. Results show attention pooling performs best overall, while simpler models remain competitive, informing practical deployment in healthcare settings.",
    figures: [
      { src: pdf("performance.png"), alt: "Classifier performance comparison", width: "70%" },
      { src: pdf("topics.png"), alt: "Topic distribution", width: "50%" },
    ],
  },
];

export const navLinks = [
  { to: "/", label: "Home" },
  { to: "/photography", label: "Photography" },
  { to: "/videos", label: "Videos" },
  { to: "/hobbies", label: "Hobbies" },
  { to: "/essays", label: "Essays" },
];

export const youtubeThumb = (id: string) =>
  `https://i.ytimg.com/vi/${id}/maxresdefault.jpg`;
