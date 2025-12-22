import { useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import { FileUp, FileCheck, Sparkles, LogOut, Loader2, AlertCircle, CheckCircle2 } from "lucide-react";

interface GradingResult {
  score: number;
  totalQuestions: number;
  wrongAnswers: {
    question: string;
    studentAnswer: string;
    correctAnswer: string;
  }[];
  feedback: string;
}

const Grading = () => {
  const [studentFile, setStudentFile] = useState<File | null>(null);
  const [keyFile, setKeyFile] = useState<File | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<GradingResult | null>(null);
  const navigate = useNavigate();

  const handleFileUpload = useCallback(
    (type: "student" | "key") => (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) {
        if (type === "student") {
          setStudentFile(file);
          toast.success(`Student sheet uploaded: ${file.name}`);
        } else {
          setKeyFile(file);
          toast.success(`Answer key uploaded: ${file.name}`);
        }
      }
    },
    []
  );

  const handleAnalyze = async () => {
    if (!studentFile || !keyFile) {
      toast.error("Please upload both files before analyzing");
      return;
    }

    setIsAnalyzing(true);
    setResult(null);

    try {
      // Read file contents
      const studentContent = await readFileContent(studentFile);
      const keyContent = await readFileContent(keyFile);

      // Call the edge function
      const response = await fetch(
        `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/grade-exam`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_ANON_KEY}`,
          },
          body: JSON.stringify({
            studentAnswers: studentContent,
            answerKey: keyContent,
          }),
        }
      );

      if (!response.ok) {
        throw new Error("Failed to analyze exam");
      }

      const data = await response.json();
      setResult(data);
      toast.success("Analysis complete!");
    } catch (error) {
      console.error("Analysis error:", error);
      toast.error("Failed to analyze. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  const readFileContent = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => resolve(e.target?.result as string);
      reader.onerror = reject;
      reader.readAsText(file);
    });
  };

  const handleLogout = () => {
    toast.success("Logged out successfully");
    navigate("/");
  };

  return (
    <div className="min-h-screen gradient-hero p-4 md:p-8">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl gradient-primary shadow-button flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-foreground">ExamGrader</h1>
              <p className="text-sm text-muted-foreground">AI-Powered Evaluation</p>
            </div>
          </div>
          <Button variant="outline" size="sm" onClick={handleLogout}>
            <LogOut className="w-4 h-4 mr-2" />
            Logout
          </Button>
        </div>

        {/* Upload Section */}
        <div className="grid md:grid-cols-2 gap-6 mb-8">
          {/* Student Sheet Upload */}
          <Card className="shadow-card border-0 animate-slide-up">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileUp className="w-5 h-5 text-primary" />
                Student's Exam Sheet
              </CardTitle>
              <CardDescription>
                Upload the student's answers for evaluation
              </CardDescription>
            </CardHeader>
            <CardContent>
              <label className="block">
                <div
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 hover:border-primary hover:bg-primary/5 ${
                    studentFile ? "border-accent bg-accent/5" : "border-border"
                  }`}
                >
                  {studentFile ? (
                    <div className="flex flex-col items-center gap-2">
                      <FileCheck className="w-10 h-10 text-accent" />
                      <p className="font-medium text-foreground">{studentFile.name}</p>
                      <p className="text-sm text-muted-foreground">Click to replace</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <FileUp className="w-10 h-10 text-muted-foreground" />
                      <p className="font-medium text-foreground">Drop file here or click to upload</p>
                      <p className="text-sm text-muted-foreground">Supports TXT, PDF, DOC files</p>
                    </div>
                  )}
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept=".txt,.pdf,.doc,.docx"
                  onChange={handleFileUpload("student")}
                />
              </label>
            </CardContent>
          </Card>

          {/* Answer Key Upload */}
          <Card className="shadow-card border-0 animate-slide-up" style={{ animationDelay: "0.1s" }}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <FileCheck className="w-5 h-5 text-primary" />
                Exam Answer Key
              </CardTitle>
              <CardDescription>
                Upload the correct answers for comparison
              </CardDescription>
            </CardHeader>
            <CardContent>
              <label className="block">
                <div
                  className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all duration-200 hover:border-primary hover:bg-primary/5 ${
                    keyFile ? "border-accent bg-accent/5" : "border-border"
                  }`}
                >
                  {keyFile ? (
                    <div className="flex flex-col items-center gap-2">
                      <FileCheck className="w-10 h-10 text-accent" />
                      <p className="font-medium text-foreground">{keyFile.name}</p>
                      <p className="text-sm text-muted-foreground">Click to replace</p>
                    </div>
                  ) : (
                    <div className="flex flex-col items-center gap-2">
                      <FileUp className="w-10 h-10 text-muted-foreground" />
                      <p className="font-medium text-foreground">Drop file here or click to upload</p>
                      <p className="text-sm text-muted-foreground">Supports TXT, PDF, DOC files</p>
                    </div>
                  )}
                </div>
                <input
                  type="file"
                  className="hidden"
                  accept=".txt,.pdf,.doc,.docx"
                  onChange={handleFileUpload("key")}
                />
              </label>
            </CardContent>
          </Card>
        </div>

        {/* Analyze Button */}
        <div className="flex justify-center mb-8 animate-slide-up" style={{ animationDelay: "0.2s" }}>
          <Button
            size="lg"
            onClick={handleAnalyze}
            disabled={!studentFile || !keyFile || isAnalyzing}
            className="px-12"
          >
            {isAnalyzing ? (
              <>
                <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                Analyzing with AI...
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5 mr-2" />
                Compare & Grade Exam
              </>
            )}
          </Button>
        </div>

        {/* Results Section */}
        {result && (
          <Card className="shadow-card border-0 animate-slide-up">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <CheckCircle2 className="w-6 h-6 text-accent" />
                Grading Results
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Score Display */}
              <div className="text-center p-6 rounded-xl bg-primary/5 border border-primary/20">
                <p className="text-muted-foreground mb-2">Final Score</p>
                <p className="text-5xl font-bold text-primary">
                  {result.score} <span className="text-2xl text-muted-foreground">/ 10</span>
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  {result.totalQuestions - result.wrongAnswers.length} correct out of {result.totalQuestions} questions
                </p>
              </div>

              {/* Wrong Answers */}
              {result.wrongAnswers.length > 0 && (
                <div>
                  <h3 className="font-semibold text-foreground mb-4 flex items-center gap-2">
                    <AlertCircle className="w-5 h-5 text-destructive" />
                    Incorrect Answers ({result.wrongAnswers.length})
                  </h3>
                  <div className="space-y-3">
                    {result.wrongAnswers.map((wrong, index) => (
                      <div
                        key={index}
                        className="p-4 rounded-lg bg-destructive/5 border border-destructive/20"
                      >
                        <p className="font-medium text-foreground mb-2">{wrong.question}</p>
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <span className="text-muted-foreground">Student's answer: </span>
                            <span className="text-destructive font-medium">{wrong.studentAnswer}</span>
                          </div>
                          <div>
                            <span className="text-muted-foreground">Correct answer: </span>
                            <span className="text-accent font-medium">{wrong.correctAnswer}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Feedback */}
              <div className="p-4 rounded-lg bg-muted">
                <h3 className="font-semibold text-foreground mb-2">AI Feedback</h3>
                <p className="text-muted-foreground">{result.feedback}</p>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Grading;
