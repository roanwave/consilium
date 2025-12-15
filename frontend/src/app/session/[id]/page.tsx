"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { getConfig, submitAnswers } from "@/lib/api";
import type { Question, CoreAnswers } from "@/lib/types";

interface ConfigResponse {
  core_questions: Question[];
  expert_followups: Record<string, Question[]>;
}

export default function InterrogationPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [coreAnswers, setCoreAnswers] = useState<CoreAnswers>({});
  const [expertAnswers, setExpertAnswers] = useState<Record<string, string>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadConfig() {
      try {
        const data = await getConfig(sessionId);
        setConfig(data);

        // Initialize core answers
        const initialCore: CoreAnswers = {};
        data.core_questions.forEach((q: Question) => {
          initialCore[q.id] = "";
        });
        setCoreAnswers(initialCore);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load configuration");
      } finally {
        setIsLoading(false);
      }
    }

    loadConfig();
  }, [sessionId]);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      await submitAnswers(sessionId, coreAnswers, expertAnswers);
      router.push(`/session/${sessionId}/deliberation`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit answers");
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateCoreAnswer = (questionId: string, value: string) => {
    setCoreAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const updateExpertAnswer = (expertQuestionKey: string, value: string) => {
    setExpertAnswers((prev) => ({ ...prev, [expertQuestionKey]: value }));
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <div className="animate-pulse text-war-accent">Loading interrogation form...</div>
      </div>
    );
  }

  if (error && !config) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <p className="text-red-500">{error}</p>
        <Button onClick={() => router.push("/")} className="mt-4">
          Return Home
        </Button>
      </div>
    );
  }

  const expertNames = config ? Object.keys(config.expert_followups) : [];

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-war-text mb-2">Scenario Interrogation</h1>
        <p className="text-war-muted">
          Answer the following questions to provide context for expert analysis.
        </p>
      </div>

      <Tabs defaultValue="core" className="space-y-6">
        <TabsList className="grid w-full grid-cols-2 lg:grid-cols-4">
          <TabsTrigger value="core">Core Questions</TabsTrigger>
          {expertNames.slice(0, 3).map((expert) => (
            <TabsTrigger key={expert} value={expert} className="capitalize">
              {expert}
            </TabsTrigger>
          ))}
        </TabsList>

        {/* Core Questions */}
        <TabsContent value="core">
          <Card className="war-panel">
            <CardHeader>
              <CardTitle className="text-war-accent">Core Questions</CardTitle>
              <CardDescription>
                These foundational questions help establish the key parameters of your scenario.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {config?.core_questions.map((question) => (
                <QuestionField
                  key={question.id}
                  question={question}
                  value={coreAnswers[question.id] || ""}
                  onChange={(value) => updateCoreAnswer(question.id, value)}
                />
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Expert-specific questions */}
        {expertNames.map((expert) => (
          <TabsContent key={expert} value={expert}>
            <Card className="war-panel">
              <CardHeader>
                <CardTitle className="text-war-accent capitalize">{expert} Expert</CardTitle>
                <CardDescription>
                  Additional questions to inform the {expert} analysis perspective.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {config?.expert_followups[expert]?.map((question) => {
                  const key = `${expert}_${question.id}`;
                  return (
                    <QuestionField
                      key={key}
                      question={question}
                      value={expertAnswers[key] || ""}
                      onChange={(value) => updateExpertAnswer(key, value)}
                    />
                  );
                })}
              </CardContent>
            </Card>
          </TabsContent>
        ))}
      </Tabs>

      {error && <p className="text-red-500 text-sm mt-4">{error}</p>}

      <div className="mt-8 flex justify-end gap-4">
        <Button variant="outline" onClick={() => router.push("/")}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          disabled={isSubmitting}
          className="bg-war-accent hover:bg-war-accentMuted text-black font-semibold"
        >
          {isSubmitting ? "Submitting..." : "Begin Deliberation"}
        </Button>
      </div>
    </div>
  );
}

function QuestionField({
  question,
  value,
  onChange,
}: {
  question: Question;
  value: string;
  onChange: (value: string) => void;
}) {
  const isLongAnswer = question.type === "textarea" || question.text.length > 100;

  return (
    <div className="space-y-2">
      <Label htmlFor={question.id} className="text-war-text">
        {question.text}
        {question.required && <span className="text-war-accent ml-1">*</span>}
      </Label>
      {isLongAnswer ? (
        <Textarea
          id={question.id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={question.placeholder || "Enter your response..."}
          className="bg-war-bg border-war-border text-war-text placeholder:text-war-muted min-h-[100px]"
        />
      ) : (
        <Input
          id={question.id}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={question.placeholder || "Enter your response..."}
          className="bg-war-bg border-war-border text-war-text placeholder:text-war-muted"
        />
      )}
    </div>
  );
}
