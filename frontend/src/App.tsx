import React, { useState, useEffect, useRef } from "react";

function App() {
  const [message, setMessage] = useState<string>("");
  const [error, setError] = useState<string>("");
  const [mode, setMode] = useState<"insert" | "extract" | "calculate">("insert");

  // insert mode states
  const [coverFile, setCoverFile] = useState<File | null>(null);
  const [messageFile, setMessageFile] = useState<File | null>(null);
  const [useEncryption, setUseEncryption] = useState(false);
  const [useRandomStart, setUseRandomStart] = useState(false);
  const [nLSB, setNLSB] = useState<number>(1);
  const [seed, setSeed] = useState<string>("");

  // extract mode states
  const [stegoFile, setStegoFile] = useState<File | null>(null);

  // calculate mode states
  const [calcCoverFile, setCalcCoverFile] = useState<File | null>(null);
  const [calcStegoFile, setCalcStegoFile] = useState<File | null>(null);
  const [psnrResult, setPsnrResult] = useState<string>("");

  // refs
  const coverInputRef = useRef<HTMLInputElement | null>(null);
  const messageInputRef = useRef<HTMLInputElement | null>(null);
  const stegoInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    fetchMessage();
  }, []);

  // reset seed kalau kedua opsi mati
  useEffect(() => {
    if (!useEncryption && !useRandomStart) {
      setSeed("");
    }
  }, [useEncryption, useRandomStart]);

  const fetchMessage = async () => {
    try {
      const response = await fetch("http://localhost:8000/");
      const data = await response.json();
      setMessage(data.message);
    } catch (err) {
      setError("Failed to fetch message from backend");
      console.error(err);
    }
  };

  const handleUpload = async () => {
    const formData = new FormData();
    let endpoint = "";

    if (mode === "insert") {
      if (!coverFile || !messageFile) {
        alert("Pilih cover MP3 dan file pesan terlebih dahulu!");
        return;
      }
      formData.append("cover", coverFile);
      formData.append("message", messageFile);
      formData.append("useEncryption", String(useEncryption));
      formData.append("useRandomStart", String(useRandomStart));
      formData.append("nLSB", String(nLSB));
      if (useEncryption || useRandomStart) {
        formData.append("seed", seed);
      }
      endpoint = "http://localhost:8000/embed";
    } else if (mode === "extract") {
      if (!stegoFile) {
        alert("Pilih file stego MP3 terlebih dahulu!");
        return;
      }
      formData.append("stego", stegoFile);
      formData.append("seed", seed);
      endpoint = "http://localhost:8000/extract";
    } else if (mode === "calculate") {
      if (!calcCoverFile || !calcStegoFile) {
        alert("Pilih cover MP3 dan stego MP3!");
        return;
      }
      formData.append("cover", calcCoverFile);
      formData.append("stego", calcStegoFile);
      endpoint = "http://localhost:8000/calculate";
    }

    try {
      const response = await fetch(endpoint, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) throw new Error("Upload failed");

      if (mode === "insert") {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "stego_output.mp3";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        alert("File stego berhasil dibuat dan diunduh!");
      } else if (mode === "extract") {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "extracted_message.txt";
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
        alert("Pesan berhasil diekstrak dan diunduh!");
      } else if (mode === "calculate") {
        const data = await response.json();
        setPsnrResult(data.psnr ? data.psnr.toFixed(2) : "Error");
      }
    } catch (err) {
      console.error(err);
      alert("Gagal upload file");
    }
  };

  return (
    <div className="text-center bg-slate-900 w-full min-h-screen">
      {/* HEADER */}
      <div className="flex flex-col items-center justify-center border-b border-gray-600 p-4">
        <div className="text-2xl font-semibold text-white">
          Steganografi Audio Multiple-LSB
        </div>
        <div className="text-md text-gray-400">IF4020 Kriptografi</div>
      </div>

      <div className="flex flex-col w-full">
        {/* MODE PANEL */}
        <div className="w-full h-[50px] border-b border-gray-600 flex flex-row p-2 gap-2">
          <button
            onClick={() => setMode("insert")}
            className={`flex-1 ${
              mode === "insert" ? "bg-slate-800" : "bg-none"
            } text-white rounded-md`}
          >
            Insert Message
          </button>
          <button
            onClick={() => setMode("extract")}
            className={`flex-1 ${
              mode === "extract" ? "bg-slate-800" : "bg-none"
            } text-white rounded-md`}
          >
            Extract Message
          </button>
          <button
            onClick={() => setMode("calculate")}
            className={`flex-1 ${
              mode === "calculate" ? "bg-slate-800" : "bg-none"
            } text-white rounded-md`}
          >
            Calculate PSNR
          </button>
        </div>

        {/* FORM */}
        <div className="w-full mt-8 flex flex-col items-center gap-4 px-6">
          {mode === "insert" && (
            <>
              {/* COVER MP3 */}
              <input
                type="file"
                accept=".mp3"
                ref={coverInputRef}
                onChange={(e) =>
                  setCoverFile(e.target.files ? e.target.files[0] : null)
                }
                className="hidden"
              />
              <button
                onClick={() => coverInputRef.current?.click()}
                className="px-6 py-2 bg-blue-700 text-white rounded-lg hover:bg-blue-800"
              >
                Pilih Cover MP3
              </button>
              {coverFile && (
                <p className="text-gray-300">
                  Cover: <span className="font-semibold">{coverFile.name}</span>
                </p>
              )}

              {/* MESSAGE FILE */}
              <input
                type="file"
                ref={messageInputRef}
                onChange={(e) =>
                  setMessageFile(e.target.files ? e.target.files[0] : null)
                }
                className="hidden"
              />
              <button
                onClick={() => messageInputRef.current?.click()}
                className="px-6 py-2 bg-blue-700 text-white rounded-lg hover:bg-blue-800"
              >
                Pilih File Pesan
              </button>
              {messageFile && (
                <p className="text-gray-300">
                  Pesan:{" "}
                  <span className="font-semibold">{messageFile.name}</span>
                </p>
              )}

              {/* OPSI */}
              <div className="flex flex-col gap-2 text-left text-white w-full max-w-md">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={useEncryption}
                    onChange={(e) => setUseEncryption(e.target.checked)}
                  />
                  Gunakan Enkripsi
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={useRandomStart}
                    onChange={(e) => setUseRandomStart(e.target.checked)}
                  />
                  Sisip Acak (Random Start)
                </label>

                <label className="flex flex-col">
                  <span>n-LSB</span>
                  <select
                    value={nLSB}
                    onChange={(e) => setNLSB(Number(e.target.value))}
                    className="mt-1 p-2 rounded-md bg-slate-800 text-white"
                  >
                    {[1, 2, 3, 4].map((n) => (
                      <option key={n} value={n}>
                        {n}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="flex flex-col">
                  <span>Kunci Stego / Seed</span>
                  <input
                    type="text"
                    value={seed}
                    onChange={(e) => setSeed(e.target.value)}
                    disabled={!useEncryption && !useRandomStart}
                    className={`mt-1 p-2 rounded-md text-white ${
                      !useEncryption && !useRandomStart
                        ? "bg-slate-700 text-gray-500 cursor-not-allowed"
                        : "bg-slate-800"
                    }`}
                  />
                </label>
              </div>
            </>
          )}

          {mode === "extract" && (
            <>
              {/* STEGO MP3 */}
              <input
                type="file"
                accept=".mp3"
                ref={stegoInputRef}
                onChange={(e) =>
                  setStegoFile(e.target.files ? e.target.files[0] : null)
                }
                className="hidden"
              />
              <button
                onClick={() => stegoInputRef.current?.click()}
                className="px-6 py-2 bg-blue-700 text-white rounded-lg hover:bg-blue-800"
              >
                Pilih Stego MP3
              </button>
              {stegoFile && (
                <p className="text-gray-300">
                  Stego: <span className="font-semibold">{stegoFile.name}</span>
                </p>
              )}

              <label className="flex flex-col text-left text-white w-full max-w-md">
                <span>Kunci Stego / Seed</span>
                <input
                  type="text"
                  value={seed}
                  onChange={(e) => setSeed(e.target.value)}
                  className="mt-1 p-2 rounded-md bg-slate-800 text-white"
                />
              </label>
            </>
          )}

          {mode === "calculate" && (
            <>
              {/* COVER MP3 */}
              <input
                type="file"
                accept=".mp3"
                onChange={(e) =>
                  setCalcCoverFile(e.target.files ? e.target.files[0] : null)
                }
                className="text-white block w-full max-w-md py-2 px-4 rounded-md bg-slate-800 border border-slate-600"
              />
              {calcCoverFile && (
                <p className="text-gray-300">
                  Cover: <span className="font-semibold">{calcCoverFile.name}</span>
                </p>
              )}

              {/* STEGO MP3 */}
              <input
                type="file"
                accept=".mp3"
                onChange={(e) =>
                  setCalcStegoFile(e.target.files ? e.target.files[0] : null)
                }
                className="text-white block w-full max-w-md py-2 px-4 rounded-md bg-slate-800 border border-slate-600"
              />
              {calcStegoFile && (
                <p className="text-gray-300">
                  Stego: <span className="font-semibold">{calcStegoFile.name}</span>
                </p>
              )}

              {psnrResult && (
                <p className="text-white font-semibold">
                  Hasil PSNR: {psnrResult} dB
                </p>
              )}
            </>
          )}

          {/* SUBMIT */}
          <button
            onClick={handleUpload}
            className="px-6 py-2 text-white rounded-lg bg-blue-700 hover:bg-blue-800"
          >
            {mode === "insert"
              ? "Sisipkan Pesan"
              : mode === "extract"
              ? "Ekstrak Pesan"
              : "Hitung PSNR"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
