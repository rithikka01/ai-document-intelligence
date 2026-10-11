import { useState } from "react";
import "./App.css";

type Risk = {
  clause: string;
  level: "High" | "Medium" | "Low";
  explanation: string;
};

type AnalysisResult = {
  filename: string;
  risk_score: number;
  summary: string;
  risks: Risk[];
  clauses: string[];
};

type FeatureCardProps = {
  icon: string;
  title: string;
  description: string;
};

function FeatureCard({
  icon,
  title,
  description,
}: FeatureCardProps) {
  return (
    <div className="feature-card">
      <span className="feature-icon">{icon}</span>
      <h3>{title}</h3>
      <p>{description}</p>
    </div>
  );
}

function App() {
  const [file, setFile] = useState<File | null>(null);

  const [result, setResult] =
    useState<AnalysisResult | null>(null);

  const [question, setQuestion] = useState("");

  const [answer, setAnswer] = useState("");

  const [loading, setLoading] = useState(false);

  const [asking, setAsking] = useState(false);

  const [error, setError] = useState("");

  // -----------------------------
  // Select PDF
  // -----------------------------
  const handleFileChange = (
    event: React.ChangeEvent<HTMLInputElement>
  ) => {
    const selectedFile = event.target.files?.[0];

    if (!selectedFile) {
      return;
    }

    if (selectedFile.type !== "application/pdf") {
      setError("Please upload a PDF file.");
      return;
    }

    setFile(selectedFile);
    setResult(null);
    setAnswer("");
    setError("");
  };

  // -----------------------------
  // Send PDF to backend
  // -----------------------------
  const analyzeDocument = async () => {
    if (!file) {
      setError("Please select a PDF first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    const formData = new FormData();

    formData.append("file", file);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/analyze`,
        {
          method: "POST",
          body: formData,
        }
      );

      if (!response.ok) {
        throw new Error("Analysis failed");
      }

      const data = await response.json();

      setResult(data);
    } catch (error) {
      console.error(error);

      setError(
        "Could not connect to the backend. Make sure FastAPI is running."
      );
    } finally {
      setLoading(false);
    }
  };

  // -----------------------------
  // Ask question
  // -----------------------------
  const askQuestion = async () => {
    if (!question.trim()) {
      return;
    }

    setAsking(true);
    setAnswer("");

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/ask`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: question,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Question failed");
      }

      const data = await response.json();

      setAnswer(data.answer);
    } catch (error) {
      console.error(error);

      setAnswer(
        "Unable to get an answer. Make sure the backend is running."
      );
    } finally {
      setAsking(false);
    }
  };

  return (
    <div className="app">

      {/* HEADER */}
      <header className="header">
        <div className="header-content">

          <div className="logo">
            <span className="logo-icon">🤖</span>

            <div>
              <h1>AI Document Intelligence</h1>

              <p>
                Understand your documents with AI
              </p>
            </div>
          </div>

          <span className="status">
            ● AI Powered
          </span>

        </div>
      </header>


      {/* MAIN CONTENT */}
      <main className="container">

        {/* HERO */}
        <section className="hero">

          <div className="badge">
            AI CONTRACT ANALYSIS
          </div>

          <h2>
            Analyze Your
            <span> Contracts</span>
          </h2>

          <p>
            Upload a contract and let AI identify
            important clauses, potential risks,
            and key insights.
          </p>


          {/* UPLOAD AREA */}
          <div className="upload-box">

            <div className="upload-icon">
              📄
            </div>

            <h3>
              {file
                ? file.name
                : "Upload your document"}
            </h3>

            <p>
              PDF files are supported
            </p>

            <label className="choose-button">

              Choose Document

              <input
                type="file"
                accept=".pdf"
                onChange={handleFileChange}
                hidden
              />

            </label>


            {file && (
              <div className="selected-file">

                <span>✓</span>

                {file.name}

              </div>
            )}

          </div>


          {/* ANALYZE BUTTON */}
          <button
            className="analyze-button"
            onClick={analyzeDocument}
            disabled={!file || loading}
          >

            {loading
              ? "Analyzing Document..."
              : "Analyze Document →"}

          </button>


          {error && (
            <p className="error">
              {error}
            </p>
          )}

        </section>


        {/* RESULTS */}
        {result && (
          <section className="results">

            {/* RESULT HEADER */}
            <div className="result-header">

              <div>

                <div className="result-label">
                  ANALYSIS COMPLETE
                </div>

                <h2>
                  Analysis Results
                </h2>

                <p>
                  {result.filename}
                </p>

              </div>


              {/* RISK SCORE */}
              <div className="risk-score">

                <span>
                  Risk Score
                </span>

                <strong>
                  {result.risk_score}
                </strong>

                <small>
                  / 100
                </small>

              </div>

            </div>


            {/* SUMMARY */}
            <div className="summary-card">

              <div className="card-title">

                <span>📋</span>

                <h3>
                  Document Summary
                </h3>

              </div>

              <p>
                {result.summary}
              </p>

            </div>


            {/* RISK DETECTION */}
            <div className="section-card">

              <div className="card-title">

                <span>⚠️</span>

                <h3>
                  Risk Detection
                </h3>

              </div>


              {result.risks.length === 0 ? (

                <div className="no-risk">
                  ✓ No predefined risk patterns detected.
                </div>

              ) : (

                result.risks.map(
                  (risk, index) => (

                    <div
                      className="risk-item"
                      key={index}
                    >

                      <div className="risk-info">

                        <strong>
                          {risk.clause}
                        </strong>

                        <p>
                          {risk.explanation}
                        </p>

                      </div>


                      <span
                        className={`risk-level ${risk.level.toLowerCase()}`}
                      >
                        {risk.level}
                      </span>

                    </div>

                  )
                )

              )}

            </div>


            {/* CLAUSES */}
            <div className="section-card">

              <div className="card-title">

                <span>📑</span>

                <h3>
                  Detected Clauses
                </h3>

              </div>


              {result.clauses.length === 0 ? (

                <p className="muted">
                  No predefined clauses detected.
                </p>

              ) : (

                <div className="clauses">

                  {result.clauses.map(
                    (clause, index) => (

                      <div
                        className="clause"
                        key={index}
                      >

                        <span>✓</span>

                        {clause}

                      </div>

                    )
                  )}

                </div>

              )}

            </div>


            {/* AI QUESTION */}
            <div className="section-card">

              <div className="card-title">

                <span>🤖</span>

                <h3>
                  Ask AI About Your Document
                </h3>

              </div>

              <p className="muted">
                Ask questions based on the uploaded
                document.
              </p>


              <div className="question-box">

                <input
                  value={question}
                  onChange={(event) =>
                    setQuestion(event.target.value)
                  }
                  placeholder="Example: What are the termination conditions?"
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      askQuestion();
                    }
                  }}
                />

                <button
                  onClick={askQuestion}
                  disabled={asking}
                >

                  {asking
                    ? "Thinking..."
                    : "Ask AI"}

                </button>

              </div>


              {answer && (

                <div className="answer">

                  <strong>
                    🤖 AI Answer
                  </strong>

                  <p>
                    {answer}
                  </p>

                </div>

              )}

            </div>

          </section>
        )}


        {/* FEATURES */}
        <section className="features">

          <FeatureCard
            icon="🔍"
            title="Clause Analysis"
            description="Identify important clauses and terms from your documents."
          />

          <FeatureCard
            icon="⚠️"
            title="Risk Detection"
            description="Detect potentially risky contract terms automatically."
          />

          <FeatureCard
            icon="🤖"
            title="AI Q&A"
            description="Ask questions and find relevant information from your document."
          />

        </section>

      </main>


      {/* FOOTER */}
      <footer className="footer">

        <p>
          AI Document Intelligence Platform
        </p>

        <span>
          Built with Python • FastAPI • React • PostgreSQL • AI
        </span>

      </footer>

    </div>
  );
}

export default App;