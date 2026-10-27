const pptxgen = require("pptxgenjs");
const pres = new pptxgen();

pres.layout = "LAYOUT_WIDE"; // 13.3" x 7.5"
pres.author = "UsageLens";
pres.title = "UsageLens — Executive Pitch";

// ===================== PALETTE =====================
const C = {
  navy:      "1E2761",
  deepBlue:  "0D1B3E",
  ice:       "CADCFC",
  accent:    "F96167",  // coral
  gold:      "F9D423",
  white:     "FFFFFF",
  offWhite:  "F5F7FA",
  gray:      "8A94A6",
  darkGray:  "3A3F4B",
  green:     "2ECC71",
  teal:      "1ABC9C",
};

const FONT_TITLE = "Cambria";
const FONT_BODY = "Calibri";

// ===================== SLIDE 1 — TITLE =====================
{
  const slide = pres.addSlide();
  slide.background = { fill: C.deepBlue };

  // Subtle decorative circles
  slide.addShape(pres.ShapeType.ellipse, { x: -0.8, y: -1.2, w: 4, h: 4, fill: { color: C.navy, transparency: 60 } });
  slide.addShape(pres.ShapeType.ellipse, { x: 10.5, y: 4.5, w: 5, h: 5, fill: { color: C.navy, transparency: 50 } });

  slide.addText("UsageLens", {
    x: 1.0, y: 1.8, w: 11.3, h: 1.2,
    fontSize: 54, fontFace: FONT_TITLE, color: C.white, bold: true,
    isTextBox: true, margin: 0,
  });

  slide.addText("Know If Your Loaned Systems Are Being Used", {
    x: 1.0, y: 3.1, w: 9, h: 0.8,
    fontSize: 24, fontFace: FONT_BODY, color: C.ice,
    isTextBox: true, margin: 0,
  });

  slide.addShape(pres.ShapeType.rect, {
    x: 1.0, y: 4.2, w: 2.5, h: 0.04, fill: { color: C.accent },
  });

  slide.addText("SSH-Based System Usage Tracking for AMD Field Engineers", {
    x: 1.0, y: 4.6, w: 9, h: 0.5,
    fontSize: 14, fontFace: FONT_BODY, color: C.gray,
    isTextBox: true, margin: 0,
  });

  slide.addNotes("Title slide — UsageLens pitch for executive audience. Emphasize the core question: are customers actually using the expensive GPU systems we lend them?");
}

// ===================== SLIDE 2 — THE PROBLEM =====================
{
  const slide = pres.addSlide();
  slide.background = { fill: C.white };

  slide.addText("The Problem", {
    x: 0.8, y: 0.5, w: 5, h: 0.8,
    fontSize: 36, fontFace: FONT_TITLE, color: C.deepBlue, bold: true,
    isTextBox: true, margin: 0,
  });

  // Big stat callout - left
  slide.addShape(pres.ShapeType.roundRect, {
    x: 0.8, y: 1.7, w: 5.5, h: 2.2, fill: { color: C.offWhite }, shadow: { type: "outer", blur: 8, offset: 2, angle: 135, opacity: 0.15, color: "000000" }, rectRadius: 0.15,
  });

  slide.addText("$100K–$500K+", {
    x: 1.1, y: 1.9, w: 5, h: 0.8,
    fontSize: 42, fontFace: FONT_TITLE, color: C.accent, bold: true,
    isTextBox: true, margin: 0,
  });
  slide.addText("per GPU system loaned to customers\nfor evaluation (MI300X, MI325X, etc.)", {
    x: 1.1, y: 2.7, w: 5, h: 0.8,
    fontSize: 14, fontFace: FONT_BODY, color: C.darkGray,
    isTextBox: true, margin: 0, lineSpacingMultiple: 1.3,
  });

  // Problem bullet points - right
  const problems = [
    { icon: "?", text: "No visibility into whether customers\nare actually using loaned systems" },
    { icon: "!", text: "Expensive hardware may sit idle\nfor weeks or months" },
    { icon: "$", text: "No data to justify continued loans\nor reclaim underutilized systems" },
    { icon: "⏱", text: "FAEs have to ask customers directly\n— subjective and time-consuming" },
  ];

  problems.forEach((p, i) => {
    const y = 1.7 + i * 1.25;
    slide.addShape(pres.ShapeType.ellipse, {
      x: 7.0, y: y, w: 0.55, h: 0.55, fill: { color: C.accent },
    });
    slide.addText(p.icon, {
      x: 7.0, y: y, w: 0.55, h: 0.55,
      fontSize: 18, fontFace: FONT_BODY, color: C.white, bold: true,
      align: "center", valign: "middle", isTextBox: true, margin: 0,
    });
    slide.addText(p.text, {
      x: 7.75, y: y, w: 4.5, h: 0.55,
      fontSize: 13, fontFace: FONT_BODY, color: C.darkGray,
      valign: "middle", isTextBox: true, margin: 0, lineSpacingMultiple: 1.15,
    });
  });

  slide.addText("\"Is the customer even using the system?\" — the question every FAE asks", {
    x: 0.8, y: 6.5, w: 11.5, h: 0.5,
    fontSize: 14, fontFace: FONT_BODY, color: C.gray, italic: true,
    isTextBox: true, margin: 0,
  });

  slide.addNotes("Highlight the cost of loaned systems and the lack of visibility. These are real pain points FAEs face daily.");
}

// ===================== SLIDE 3 — THE SOLUTION =====================
{
  const slide = pres.addSlide();
  slide.background = { fill: C.deepBlue };

  slide.addText("The Solution", {
    x: 0.8, y: 0.5, w: 5, h: 0.8,
    fontSize: 36, fontFace: FONT_TITLE, color: C.white, bold: true,
    isTextBox: true, margin: 0,
  });

  slide.addText("UsageLens — a lightweight, self-hosted web tool that\nSSHs into remote systems and answers the question with data.", {
    x: 0.8, y: 1.3, w: 11, h: 0.7,
    fontSize: 16, fontFace: FONT_BODY, color: C.ice,
    isTextBox: true, margin: 0, lineSpacingMultiple: 1.3,
  });

  // Four capability cards
  const caps = [
    { title: "Login Tracking", desc: "Who logged in, when,\nand for how long", metric: "last", color: C.teal },
    { title: "GPU Utilization", desc: "Track GPU usage % over\ntime via rocm-smi", metric: "rocm-smi", color: C.accent },
    { title: "System Load", desc: "CPU load averages\nand uptime trends", metric: "uptime", color: C.gold },
    { title: "Zero Install", desc: "No agent on target —\njust SSH access", metric: "SSH only", color: C.green },
  ];

  caps.forEach((cap, i) => {
    const x = 0.8 + i * 3.05;
    slide.addShape(pres.ShapeType.roundRect, {
      x: x, y: 2.5, w: 2.75, h: 3.2, fill: { color: C.navy }, shadow: { type: "outer", blur: 10, offset: 3, angle: 135, opacity: 0.3, color: "000000" }, rectRadius: 0.15,
    });
    // Color top accent
    slide.addShape(pres.ShapeType.roundRect, {
      x: x, y: 2.5, w: 2.75, h: 0.08, fill: { color: cap.color }, rectRadius: 0.04,
    });
    slide.addText(cap.title, {
      x: x + 0.2, y: 2.85, w: 2.35, h: 0.5,
      fontSize: 18, fontFace: FONT_TITLE, color: C.white, bold: true,
      isTextBox: true, margin: 0,
    });
    slide.addText(cap.desc, {
      x: x + 0.2, y: 3.4, w: 2.35, h: 0.8,
      fontSize: 13, fontFace: FONT_BODY, color: C.ice,
      isTextBox: true, margin: 0, lineSpacingMultiple: 1.3,
    });
    slide.addText(cap.metric, {
      x: x + 0.2, y: 4.8, w: 2.35, h: 0.4,
      fontSize: 11, fontFace: FONT_BODY, color: cap.color, italic: true,
      isTextBox: true, margin: 0,
    });
  });

  slide.addNotes("Four pillars of what UsageLens tracks. Emphasize zero installation on customer side — just SSH.");
}

// ===================== SLIDE 4 — KEY FEATURES =====================
{
  const slide = pres.addSlide();
  slide.background = { fill: C.white };

  slide.addText("Key Features", {
    x: 0.8, y: 0.5, w: 5, h: 0.8,
    fontSize: 36, fontFace: FONT_TITLE, color: C.deepBlue, bold: true,
    isTextBox: true, margin: 0,
  });

  const features = [
    { title: "Collect All", desc: "One-click collection from every monitored host with per-host status" },
    { title: "Historical Dashboards", desc: "Pie charts showing utilization vs idle time — 1 week to 3 months" },
    { title: "GPU Tracking", desc: "AMD ROCm + NVIDIA support — avg and peak utilization over time" },
    { title: "Jump Host Support", desc: "Reach systems behind firewalls via SSH jump hosts" },
    { title: "Auto-Polling", desc: "Hands-off monitoring at 1h to 24h intervals — data accumulates automatically" },
    { title: "Snapshot Browser", desc: "Drill into any point in time — see who was logged in, GPU state, load" },
    { title: "Login History", desc: "Session durations per user from Linux `last` — not just who's online now" },
    { title: "Copy Configs", desc: "Duplicate host setups for quick onboarding of similar systems" },
  ];

  features.forEach((f, i) => {
    const col = i < 4 ? 0 : 1;
    const row = i % 4;
    const x = 0.8 + col * 6.2;
    const y = 1.6 + row * 1.35;

    slide.addShape(pres.ShapeType.roundRect, {
      x: x, y: y, w: 5.9, h: 1.1, fill: { color: C.offWhite }, shadow: { type: "outer", blur: 4, offset: 1, angle: 135, opacity: 0.1, color: "000000" }, rectRadius: 0.1,
    });
    slide.addText(f.title, {
      x: x + 0.25, y: y + 0.12, w: 5.4, h: 0.35,
      fontSize: 15, fontFace: FONT_BODY, color: C.deepBlue, bold: true,
      isTextBox: true, margin: 0,
    });
    slide.addText(f.desc, {
      x: x + 0.25, y: y + 0.5, w: 5.4, h: 0.4,
      fontSize: 12, fontFace: FONT_BODY, color: C.gray,
      isTextBox: true, margin: 0,
    });
  });

  slide.addNotes("Eight key features — emphasize auto-polling and GPU tracking as differentiators.");
}

// ===================== SLIDE 5 — HOW IT WORKS =====================
{
  const slide = pres.addSlide();
  slide.background = { fill: C.offWhite };

  slide.addText("How It Works", {
    x: 0.8, y: 0.5, w: 5, h: 0.8,
    fontSize: 36, fontFace: FONT_TITLE, color: C.deepBlue, bold: true,
    isTextBox: true, margin: 0,
  });

  // Flow diagram boxes
  const steps = [
    { label: "FAE's Laptop", sub: "Browser UI\nlocalhost:8000", color: C.teal },
    { label: "SSH", sub: "Encrypted\nconnection", color: C.gray },
    { label: "Jump Host", sub: "Optional\nfirewall hop", color: C.gold },
    { label: "SSH", sub: "Via alias\ne.g. ssh gpu-3", color: C.gray },
    { label: "Target System", sub: "MI300X / MI325X\nrocm-smi + last", color: C.accent },
  ];

  steps.forEach((s, i) => {
    const x = 0.6 + i * 2.5;
    const isArrow = s.label === "SSH";

    if (isArrow) {
      slide.addShape(pres.ShapeType.rect, {
        x: x + 0.3, y: 2.95, w: 1.5, h: 0.06, fill: { color: C.darkGray },
      });
      slide.addShape(pres.ShapeType.isoscelesTriangle, {
        x: x + 1.6, y: 2.75, w: 0.35, h: 0.45, fill: { color: C.darkGray }, rotate: 90,
      });
      slide.addText(s.sub, {
        x: x + 0.1, y: 3.3, w: 2, h: 0.5,
        fontSize: 10, fontFace: FONT_BODY, color: C.gray, align: "center",
        isTextBox: true, margin: 0, lineSpacingMultiple: 1.2,
      });
    } else {
      slide.addShape(pres.ShapeType.roundRect, {
        x: x, y: 2.1, w: 2.2, h: 1.8, fill: { color: C.white },
        shadow: { type: "outer", blur: 8, offset: 2, angle: 135, opacity: 0.15, color: "000000" }, rectRadius: 0.15,
      });
      slide.addShape(pres.ShapeType.roundRect, {
        x: x, y: 2.1, w: 2.2, h: 0.07, fill: { color: s.color }, rectRadius: 0.04,
      });
      slide.addText(s.label, {
        x: x + 0.15, y: 2.4, w: 1.9, h: 0.45,
        fontSize: 16, fontFace: FONT_TITLE, color: C.deepBlue, bold: true, align: "center",
        isTextBox: true, margin: 0,
      });
      slide.addText(s.sub, {
        x: x + 0.15, y: 2.9, w: 1.9, h: 0.7,
        fontSize: 11, fontFace: FONT_BODY, color: C.gray, align: "center",
        isTextBox: true, margin: 0, lineSpacingMultiple: 1.3,
      });
    }
  });

  // Tech stack bar
  slide.addShape(pres.ShapeType.roundRect, {
    x: 0.8, y: 4.8, w: 11.7, h: 1.8, fill: { color: C.white },
    shadow: { type: "outer", blur: 6, offset: 2, angle: 135, opacity: 0.1, color: "000000" }, rectRadius: 0.12,
  });

  const techs = [
    { label: "Python / FastAPI", desc: "Backend server" },
    { label: "Chart.js", desc: "Visualizations" },
    { label: "Paramiko", desc: "SSH connections" },
    { label: "YAML Storage", desc: "No database needed" },
    { label: "Any OS", desc: "Windows · Linux · Mac" },
  ];

  techs.forEach((t, i) => {
    const x = 1.1 + i * 2.3;
    slide.addText(t.label, {
      x: x, y: 5.0, w: 2, h: 0.4,
      fontSize: 14, fontFace: FONT_BODY, color: C.deepBlue, bold: true, align: "center",
      isTextBox: true, margin: 0,
    });
    slide.addText(t.desc, {
      x: x, y: 5.4, w: 2, h: 0.35,
      fontSize: 11, fontFace: FONT_BODY, color: C.gray, align: "center",
      isTextBox: true, margin: 0,
    });
  });

  slide.addNotes("Architecture overview — emphasize simplicity: runs on a laptop, no cloud, no database, no install on customer side.");
}

// ===================== SLIDE 6 — IMPACT =====================
{
  const slide = pres.addSlide();
  slide.background = { fill: C.deepBlue };

  slide.addShape(pres.ShapeType.ellipse, { x: 9.5, y: -1.5, w: 6, h: 6, fill: { color: C.navy, transparency: 50 } });

  slide.addText("Impact", {
    x: 0.8, y: 0.5, w: 5, h: 0.8,
    fontSize: 36, fontFace: FONT_TITLE, color: C.white, bold: true,
    isTextBox: true, margin: 0,
  });

  const impacts = [
    { stat: "Data > Guesswork", desc: "Turn \"Is the customer using it?\" from a phone call into a dashboard" },
    { stat: "Reclaim Idle Systems", desc: "Identify hardware sitting unused — reallocate to active evaluations" },
    { stat: "Prove ROI", desc: "Quantify customer engagement hours for business justification" },
    { stat: "Zero Customer Friction", desc: "No software to install, no firewall changes — just existing SSH access" },
  ];

  impacts.forEach((imp, i) => {
    const y = 1.7 + i * 1.3;
    slide.addShape(pres.ShapeType.roundRect, {
      x: 0.8, y: y, w: 11.7, h: 1.05, fill: { color: C.navy },
      shadow: { type: "outer", blur: 6, offset: 2, angle: 135, opacity: 0.2, color: "000000" }, rectRadius: 0.1,
    });
    slide.addText(imp.stat, {
      x: 1.1, y: y + 0.1, w: 4.5, h: 0.4,
      fontSize: 20, fontFace: FONT_TITLE, color: C.accent, bold: true,
      isTextBox: true, margin: 0,
    });
    slide.addText(imp.desc, {
      x: 1.1, y: y + 0.5, w: 10.5, h: 0.4,
      fontSize: 14, fontFace: FONT_BODY, color: C.ice,
      isTextBox: true, margin: 0,
    });
  });

  slide.addText("UsageLens — Built by FAEs, for FAEs", {
    x: 0.8, y: 6.6, w: 11.5, h: 0.5,
    fontSize: 18, fontFace: FONT_TITLE, color: C.gold, bold: true,
    align: "center", isTextBox: true, margin: 0,
  });

  slide.addNotes("Close with impact — data replaces guesswork, idle systems get reclaimed, and there's zero friction for the customer.");
}

// ===================== GENERATE =====================
pres.writeFile({ fileName: "UsageLens_Pitch.pptx" }).then(() => {
  console.log("Created: UsageLens_Pitch.pptx");
});
