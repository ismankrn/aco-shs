# Kerangka Manuskrip Paper 2 — Poin per Kalimat

Target jurnal: PeerJ Computer Science. Bahasa: Inggris.
Prinsip dokumen ini: **satu bullet = inti satu kalimat** — kalimat ditulis oleh penulis,
bukan oleh asisten. Tanda `[P3]` = menunggu data P3; `[refX]` merujuk daftar referensi
di bagian akhir. Angka yang tercantum sudah final dari results/*.csv.

---

## Kandidat judul (pilih/tulis sendiri, ≤ 15 kata)

1. Fokus kerangka: *sequential hybrid sampling with informed undersampling* + evaluasi lintas 4 dataset DTI
2. Fokus temuan: seleksi terinformasi (ACO/SA) atas pool sintetis — kapan berguna, kapan tidak
3. Fokus metodologi: evaluasi berulang multi-seed membalikkan kesimpulan split-tunggal pada DTI imbalanced

---

## Abstract (8–10 kalimat)

- Konteks: prediksi DTI penting untuk penemuan obat; dataset DTI sangat imbalanced
- Masalah: studi sebelumnya (termasuk paper 1) mengevaluasi dengan split tunggal → rapuh
- Metode: kerangka SHS (oversampling melebihi mayoritas → undersampling terinformasi ACO/SA);
  evaluasi 4 dataset Yamanishi, protokol multi-seed, uji statistik berpasangan
- Kontribusi tambahan: koreksi implementasi ACO paper 1 + ablasi menyeluruh + pembanding SA budget-matched
- Hasil 1: hasil paper 1 tereproduksi tetapi terbukti sensitif seed (F1 36,1% ± 7,1%; angka tesis = ujung optimis)
- Hasil 2: ACO robust terhadap aturan/parameter; SA setara ACO → nilai ada pada seleksi terinformasi
- Hasil 3 [P3]: manfaat SHS bergantung dataset — nyata di NR (kecil/ekstrem), menyusut di dataset besar
- Hasil 4: biaya komputasi seleksi terinformasi 500–1.700× seleksi acak → trade-off eksplisit
- Kesimpulan: peta kapan SHS layak dipakai + protokol evaluasi yang direkomendasikan

---

## 1. Introduction (5–6 paragraf)

**Par. 1 — konteks DTI** (ringkas; jangan ulang paper 1 panjang-panjang)
- DTI = interaksi obat–protein target; kunci drug discovery/repositioning [ref1, ref3]
- Eksperimen lab mahal/lambat → prediksi komputasional [ref2]
- Karakter data: negatif tak terverifikasi + imbalance ekstrem (NR: 6% positif) [ref4]

**Par. 2 — penanganan imbalance & posisi SHS**
- Tiga keluarga data-level: oversampling, undersampling, hybrid [ref10, ref13]
- Oversampling klasik: ROS/SMOTE/ADASYN [ref8, ref9]; hybrid mapan: SMOTE-ENN, SMOTE-Tomek [refN1]
- SHS (paper 1): oversampling MELEBIHI mayoritas → undersampling memangkas kembali; pembeda vs hybrid biasa
- Seleksi terinformasi via metaheuristik: ACOSampling [ref15], SAUS [refN2 konsep, ref16], FF-SMOTE [ref18]

**Par. 3 — celah yang ditinggalkan paper 1 (motivasi inti)**
- Paper 1: satu dataset (NR), satu split, tanpa uji statistik, tanpa pembanding hybrid mapan
- Tidak diketahui: generalisasi lintas dataset, sensitivitas seed, apakah ACO spesifik atau seleksi terinformasi generik
- (Jujur, framing positif: "extend and stress-test" — bukan menjatuhkan paper 1)

**Par. 4 — pertanyaan riset**
- RQ1 generalisasi 4 dataset; RQ2 vs hybrid mapan; RQ3 koreksi & ablasi implementasi ACO; RQ4 fitness; (RQ5 implisit: ACO vs SA budget-matched)

**Par. 5 — kontribusi (bullet list di paper)**
- Protokol evaluasi berulang + statistik berpasangan untuk SHS-DTI (pertama untuk keluarga metode ini)
- Koreksi implementasi tervalidasi reproduksi + temuan robustness
- Pembanding SA budget-matched → klaim "informed selection, not the metaheuristic"
- Peta praktis: pasangan oversampler×selektor×rasio per karakter dataset + biaya runtime
- Kode & data publik (GitHub) → reproducibility penuh

---

## 2. Methods — POIN PER KALIMAT (draf lengkap)

### 2.1 Datasets

- Empat dataset gold-standard Yamanishi [ref24]: NR, GPCR, IC, Enzyme (kelas protein target berbeda)
- Fitur dari pipeline SRX-DTI [ref23]: FP2 fingerprint obat 256-bit (OpenBabel) + AAC 20 + DPC 400 protein
- Semua fitur min-max per kolom dalam dataset; pasangan = produk kartesius penuh obat×protein
- Label 1 = interaksi gold standard; label 0 = pasangan tak berlabel (asumsi negatif — caveat standar bidang ini)
- Tabel 1: statistik 4 dataset (pasangan, positif, %): NR 1.404/90/6,41; GPCR 21.185/635/3,00; IC 42.840/1.476/3,45; Enzyme 295.480/2.926/0,99
- NR identik byte dengan data paper 1 (kontinuitas terverifikasi md5)
- Tanpa feature selection — mengisolasi efek sampling (desain sengaja, ikuti paper 1)

### 2.2 Kerangka SHS

- Definisi: (i) oversample minoritas MELEBIHI mayoritas ke target = rasio × n_mayoritas; (ii) undersample pool sintetis kembali ke seimbang
- Beda vs hybrid klasik (SMOTE-ENN/Tomek): SHS memilih SUBSET sintetis via optimasi, bukan membersihkan noise pasca-hoc
- Rasio ∈ {1,0; 1,25; 1,5} — berbasis rasio (bukan absolut paper 1) agar portabel lintas dataset
- Rasio 1,0 = kontrol degenerate (pool ≈ kebutuhan; selektor nyaris tanpa pilihan)
- Oversampler: ROS [ref10], SMOTE k=11 [ref8], ADASYN [ref9]; selektor: RUS (acak) vs ACO vs SA (terinformasi)

### 2.3 ACO undersampler

- Solusi = multiset indeks berukuran (n_mayoritas − n_minoritas) atas pool sintetis
- Probabilitas seleksi ∝ pheromone per instans (roulette wheel); persamaan P_i = τ_i / Σ τ_i
- Update pheromone STANDAR: τ_new = (1−ρ)·τ_old + Δ; Δ = akumulasi fitness semut pemilih [ref20]
- Fitness = F1 rata-rata 5-fold CV STRATIFIED pada data latih asli; sintetis hanya masuk fold-train
- Parameter (tuning paper 1 + sensitivitas §3.x): τ0=0,3; ρ=0,8; K semut; N=10 iterasi; early-stop idle 5

**2.3.1 Koreksi terhadap implementasi paper 1** (subbagian eksplisit — kejujuran = kekuatan)
- Ditemukan 3 divergensi kode-vs-persamaan di implementasi asli:
  (a) update pheromone kode = (1−ρ·τ)+Δ ≠ persamaan publikasi
  (b) CV fitness tanpa stratifikasi (fold bisa tanpa positif pada imbalance 6%)
  (c) seleksi with-replacement (solusi bisa berisi duplikat sintetis)
- Ketiganya diablasi penuh 2×2×2 (hasil §3.2: tidak ada yang signifikan → robust)
- Konfigurasi final: rumus standar + stratified + with-replacement (konsisten persamaan publikasi)

### 2.4 Pembanding SA (budget-matched)

- Motivasi: memisahkan "manfaat seleksi terinformasi" dari "manfaat ACO spesifik" [ref16 sebagai preseden SA]
- SA klasik [refN2]: satu solusi berjalan; tetangga = resample 5% posisi; penerimaan Boltzmann exp(Δ/T)
- Cooling geometrik T: 0,05 → 0,001 sepanjang budget
- Budget evaluasi fitness = K×N milik ACO (identik), fungsi fitness & ruang solusi identik
- Klaim fairness: satu-satunya perbedaan = strategi pencarian

### 2.5 Metode pembanding

- 13 metode total per dataset: baseline GB; ROS/SMOTE/ADASYN klasik; SMOTE-ENN, SMOTE-Tomek [refN1];
  SHS-RUS ×3; SHS-ACO ×3; SHS-SA (SMOTE)
- Classifier seragam: Gradient Boosting [refN3] (pemenang baseline paper 1; RF pembanding baseline)
- Alasan tidak menambah classifier lain: isolasi efek sampling (rujuk desain)

### 2.6 Desain eksperimen (fase)

- P0 reproduksi: konfigurasi persis paper 1, 5 seed → kuantifikasi sensitivitas split tunggal
- P0b ekuivalensi GB vs HistGB (10 seed berpasangan) → keputusan mesin komputasi
- P1 ablasi 2×2×2 koreksi ACO + fitness {F1, G-Mean, BAS} (NR, 5 seed, Wilcoxon berpasangan)
- P2 pilot rasio {1,0; 1,25; 1,5} × 6 metode SHS (NR) → rasio final per lengan
- P2b sensitivitas ρ {0,5; 0,95}, K {10; 40} + duel SA (NR)
- P3 perbandingan penuh 13 metode × 4 dataset; seed 0–9 metode murah, 0–4 ACO/SA
- Split: stratified 70/30 per seed; sampling HANYA pada train; seed identik antar metode (berpasangan)
- Keputusan berbasis pilot: K=10 (dari P2b, setara K=20 pada separuh biaya); rasio per lengan
  (RUS 1,25/1,25/1,0; ACO/SA 1,5 semua — pola: selektor terinformasi menyukai pool besar)
- Enzyme: fitness pakai HistGB (fit GB klasik 810 dtk vs HistGB 82,7 dtk — GB infeasible),
  classifier final tetap GB; seragam antar metode dalam dataset → perbandingan internal tetap adil
- Kompute: server cloud 12 vCPU; OMP_NUM_THREADS=1; job per-seed paralel

### 2.7 Metrik & uji statistik

- Metrik: F1 (primer), G-Mean, BAS — standar imbalance [ref25]; + AUPRC (threshold-free, tepat utk imbalance) [refN4]
- Semua dari confusion matrix pada test set tak tersentuh; accuracy dilaporkan hanya sbg ilustrasi paradoks
- Per dataset: Wilcoxon signed-rank berpasangan (seed sama), α=0,05
- Lintas dataset: Friedman + post-hoc Nemenyi pada blok dataset×seed, mean ranks [refN5]
- Runtime dilaporkan per metode (mesin sama, disclaimer paralelisme)

### 2.8 Implementasi & reproducibility

- Python 3.12; scikit-learn [refN6], imbalanced-learn [refN7]
- Semua run ber-seed penuh → deterministik (bukti: baris identik lintas mesin/waktu)
- Kode, pipeline data, dan seluruh CSV hasil: repositori publik (URL GitHub; buat rilis/tag saat submit)
- Data availability: fitur dari repo SRX-DTI [ref23]; skrip regenerasi disertakan

---

## 3. Results (struktur + poin yang sudah final)

### 3.1 Reproduksi & sensitivitas seed (Tabel 2)
- Konfigurasi paper 1: F1 = 0,3606 ± 0,0707 (5 seed), rentang 0,2667–0,4314
- 2/5 seed tepat di 0,4314 ≈ angka publikasi 0,4324 → tereproduksi, tapi ujung optimis
- 1 TP ≈ 4,3 poin recall di NR (27 positif test) → argumen protokol berulang

### 3.2 Ablasi & sensitivitas ACO (Tabel 3)
- Per faktor (n=20 pasangan): legacy p=0,925; stratified p=0,554; replacement p=0,112
- Refined vs thesis-like: p=1,0 → koreksi tidak mengubah hasil (robustness)
- Fitness: F1 0,3381 ≈ G-Mean 0,3389; BAS lebih buruk 0,3081
- ρ {0,5–0,95} & K {10–40} tak signifikan; K=10 = kualitas K=20 pada 52 vs 107 mnt/seed; K=40 memburuk 2× biaya
- (Bonus dari log konvergensi: fitness mendatar di iterasi ~6–8 → N=10 cukup; figur konvergensi)

### 3.3 Interaksi rasio × selektor (Tabel 4 / Figur)
- ACO terbaik selalu di rasio 1,5 (ketiga oversampler); RUS terbaik di 1,0–1,25
- Interpretasi mekanistik: surplus = ruang pilihan bagi selektor terinformasi, noise bagi selektor acak

### 3.4 ACO vs SA (Tabel 5)
- NR: SA 0,3565 vs ACO 0,3431, p=0,63; SA menang 3/5 seed → setara
- [P3] konsistensi lintas dataset

### 3.5 Perbandingan utama 4 dataset (Tabel 6 — tabel inti paper; Figur ranks)
- FINAL NR: keluarga ROS dominan (RUS-ROS 47,3%; ACO-ROS K10 43,4%) >> SMOTE (34–40%)
- FINAL GPCR: ROS runtuh (~24% semua varian); SMOTE polos 35,8% & SMOTE-Tomek 36,1% memimpin;
  ACO-SMOTE 35,2% (15,4 jam/seed) TIDAK melampaui SMOTE polos (8 dtk) — seleksi tak membayar di sini
- [P3] IC, Enzyme, SA-GPCR/ADASYN-GPCR sisanya
- [P3] Friedman/Nemenyi + mean ranks lintas dataset
- Poin lintas dataset (sudah terlihat): tidak ada juara universal; pembalikan NR↔GPCR

### 3.6 Runtime (Tabel 7 / bar chart)
- RUS 3–8 dtk/seed vs ACO 22 mnt–15,4 jam/seed (500–1.700×)
- SA ≈ ACO (budget sama); K=10 separuh K=20
- [P3] lengkap semua dataset di mesin identik

---

## 4. Discussion (poin kunci)

- Temuan payung: evaluasi split-tunggal menyesatkan — kesimpulan paper 1 (SMOTE+ACO juara)
  tidak bertahan di bawah protokol berulang maupun lintas dataset
- "Ceiling hypothesis": karakter oversampler × dataset menentukan langit-langit; selektor menentukan
  seberapa dekat ke langit-langit — ROS efektif hanya di dataset kecil/homogen (NR), interpolatif
  menang di dataset besar (GPCR) [P3: konfirmasi IC/Enzyme]
- Manfaat seleksi terinformasi menyusut saat data positif asli cukup banyak (444 vs 63) —
  hipotesis: kualitas sintetis lebih seragam → memilih tidak menambah nilai
- ACO vs SA setara → rekomendasi praktis boleh memilih yang lebih sederhana; jawaban langsung
  untuk pertanyaan "mengapa ACO" [kaitkan ref16, refN2]
- Robustness menyeluruh (aturan, parameter, optimizer) = kabar baik untuk praktisi, dan
  koreksi kode-vs-persamaan dilaporkan sebagai praktik transparansi
- Trade-off biaya: kapan 15 jam komputasi layak untuk ≤1 poin F1? — kerangka keputusan utk pembaca
- Threats to validity: asumsi negatif; 5 seed utk lengan mahal (daya uji terbatas, p min 0,0625);
  HistGB fitness khusus Enzyme; satu classifier; satu domain (DTI)
- Future work: classifier lain, dataset non-DTI, seleksi terinformasi murah (surrogate fitness),
  GA/PSO (disebut, tidak diuji)

---

## 5. Conclusion (3–5 kalimat)

- SHS valid tetapi kondisional — peta kapan-apa (dataset kecil/ekstrem: ya; besar: oversampler
  sederhana cukup)
- Seleksi terinformasi > acak pada kondisi yang tepat; metaheuristiknya bebas dipilih
- Protokol evaluasi berulang + statistik = rekomendasi baku untuk riset sampling-DTI ke depan
- Kode/data terbuka

---

## Rencana Tabel & Figur

| # | Isi | Sumber data | Status |
|---|---|---|---|
| T1 | Statistik 4 dataset | data/raw | final |
| T2 | Reproduksi per-seed vs angka paper 1 | runs_p0 | final |
| T3 | Ablasi 2×2×2 + fitness + sensitivitas ρ/K | runs_p1_merged, runs_p2b | final |
| T4 | Rasio × metode (NR) | runs_p2 | final |
| T5 | ACO vs SA per dataset | runs_p2b + runs_p3 | sebagian |
| T6 | **Tabel inti**: 13 metode × 4 dataset (F1/G-Mean/BAS/AUPRC, mean±std) | runs_p3 | [P3] |
| T7 | Runtime per metode per dataset | runs_p3 | [P3] |
| F1 | Diagram kerangka SHS (adaptasi figur paper 1) | — | gambar ulang |
| F2 | Kurva konvergensi ACO vs SA (history_) | logs | bahan ada |
| F3 | Interaksi rasio × selektor (line plot) | runs_p2 | final |
| F4 | Mean ranks Friedman (CD diagram) | runs_p3 | [P3] |
| F5 | F1 vs runtime (scatter log-x; "harga kecerdasan") | runs_p3 | [P3] |

---

## Referensi

**Dipakai ulang dari paper 1** (nomor paper 1): [1] Azlim Khan 2023, [2] You 2018, [3] Bagherian 2021,
[4] Shi 2019, [8] Chawla SMOTE, [9] He ADASYN, [10] Wongvorachan 2023, [13] Mohammed 2020,
[15] Yu ACOSampling, [16] Chennuru SAUS, [18] Kaur FF-SMOTE, [20] Dorigo ACO, [23] Khojasteh SRX-DTI,
[24] Yamanishi 2008, [25] (metrik) — DOI semuanya sudah terverifikasi di manuskrip IJ-AI.

**Baru (terverifikasi Crossref hari ini):**
- [N1] G. E. A. P. A. Batista, R. C. Prati, M. C. Monard, "A study of the behavior of several methods
  for balancing machine learning training data," ACM SIGKDD Explorations, vol. 6, no. 1, pp. 20–29,
  2004, doi: 10.1145/1007730.1007735. → §2.5 (SMOTE-ENN & SMOTE-Tomek)
- [N2] S. Kirkpatrick, C. D. Gelatt, M. P. Vecchi, "Optimization by simulated annealing," Science,
  vol. 220, no. 4598, pp. 671–680, 1983, doi: 10.1126/science.220.4598.671. → §2.4
- [N3] J. H. Friedman, "Greedy function approximation: a gradient boosting machine," Annals of
  Statistics, vol. 29, no. 5, pp. 1189–1232, 2001, doi: 10.1214/aos/1013203451. → §2.5
  (ganti sitasi GB sekunder paper 1 dengan sumber primer)
- [N4] T. Saito, M. Rehmsmeier, "The precision-recall plot is more informative than the ROC plot
  when evaluating binary classifiers on imbalanced datasets," PLoS ONE, vol. 10, no. 3, e0118432,
  2015, doi: 10.1371/journal.pone.0118432. → §2.7 (justifikasi AUPRC)
- [N5] J. Demšar, "Statistical comparisons of classifiers over multiple data sets," Journal of
  Machine Learning Research, vol. 7, pp. 1–30, 2006. (JMLR — tanpa DOI, normal) → §2.7
- [N6] F. Pedregosa et al., "Scikit-learn: machine learning in Python," JMLR, vol. 12,
  pp. 2825–2830, 2011. (tanpa DOI) → §2.8
- [N7] G. Lemaître, F. Nogueira, C. K. Aridas, "Imbalanced-learn: a Python toolbox to tackle the
  curse of imbalanced datasets in machine learning," JMLR, vol. 18, no. 17, pp. 1–5, 2017.
  (tanpa DOI) → §2.8
- [N8 opsional] G. Ke et al., "LightGBM: a highly efficient gradient boosting decision tree,"
  NeurIPS 30, 2017. (tanpa DOI) → §2.6 jika HistGB-Enzyme perlu rujukan histogram-GB

Perkiraan total referensi: ±30–35 (di atas minimum; tinjauan pustaka Introduction bisa menarik
lagi 3–5 dari daftar paper 1 bila perlu).

---

## LAMPIRAN (2026-10-08): angka final P3 — mengganti semua tanda [P3]

- Tabel inti 13x4 & semua statistik: results/analysis/P3_rekap.xlsx + docs/experiment-log.md §P3
- Juara per dataset: NR ros/rus-ros 0,457-0,473; GPCR sa-smote 0,365; IC aco-adasyn 0,346;
  Enzyme baseline 0,185 (tak terkalahkan)
- Gradien inti Discussion terkonfirmasi 4 titik: manfaat sampling & seleksi menurun monoton
  dengan kekayaan positif asli (63/444/1.033/2.048)
- Temuan baru untuk §Results & §Discussion: **properti abstensi ACO** — di Enzyme, ACO menolak
  menambah sintetis di 15/15 run (output identik baseline, terverifikasi confusion matrix);
  SA tanpa opsi abstain terpaksa oversampling dan sedikit di bawah baseline -> seleksi
  terinformasi + aksi-nol = katup pengaman; rekomendasi desain eksplisit
- SA vs ACO: tak signifikan di semua dataset (p 0,125-0,812) -> klaim "optimizer sekunder" final
- Friedman 13 metode, 20 blok: chi2=42,5 p=2,7e-5; rank teratas aco-adasyn 4,85, aco-smote 5,00,
  smote-tomek 5,62; terbawah baseline/ros/rus-ros ±9,4
- Runtime final (sheet Runtime P3_rekap): RUS/hybrid murah 2 dtk-2,5 mnt/seed; ACO/SA 22 mnt-20 jam/seed
  (500-1.700x); enzyme ACO ±11-14 jam/seed dengan fitness HistGB K=10 N=5
