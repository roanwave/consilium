"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { getSession, submitAnswers } from "@/lib/api";
import type { Question, CoreAnswers } from "@/lib/types";

// Static core questions matching backend
const CORE_QUESTIONS: Question[] = [
  {
    id: "era",
    type: "select",
    question: "What era is this battle set in?",
    options: [
      { value: "ancient", label: "Ancient (Pre-500 CE)" },
      { value: "early_medieval", label: "Early Medieval (500-1000 CE)" },
      { value: "high_medieval", label: "High Medieval (1000-1300 CE)" },
      { value: "late_medieval", label: "Late Medieval (1300-1500 CE)" },
      { value: "renaissance", label: "Renaissance (1500-1600 CE)" },
      { value: "fantasy", label: "Fantasy" },
    ],
    required: true,
  },
  {
    id: "theater",
    type: "text",
    question: "What geographic theater is this battle in?",
    placeholder: "e.g., Northern France, the Levant, fantasy kingdom",
    required: false,
  },
  {
    id: "why_battle_now",
    type: "textarea",
    question: "Why is this battle happening now? What forces the engagement?",
    placeholder: "What strategic necessity or narrative reason brings these armies together?",
    required: true,
  },
  {
    id: "army_sizes",
    type: "textarea",
    question: "What are the army sizes and key asymmetries?",
    placeholder: "e.g., 8,000 vs 12,000; defenders have fortifications; attackers have cavalry advantage",
    required: true,
  },
  {
    id: "terrain_type",
    type: "select",
    question: "What is the primary terrain type?",
    options: [
      { value: "plains", label: "Plains" },
      { value: "hills", label: "Hills" },
      { value: "mountains", label: "Mountains" },
      { value: "forest", label: "Forest" },
      { value: "marsh", label: "Marsh" },
      { value: "river_crossing", label: "River Crossing" },
      { value: "coastal", label: "Coastal" },
      { value: "urban", label: "Urban" },
      { value: "desert", label: "Desert" },
    ],
    required: true,
  },
  {
    id: "terrain_feature",
    type: "text",
    question: "What is the one defining terrain feature?",
    placeholder: "e.g., a fordable river, a steep ridge, a fortified bridge",
    required: true,
  },
  {
    id: "commander_competence_side_a",
    type: "select",
    question: "How competent is Side A's commander?",
    options: [
      { value: "incompetent", label: "Incompetent" },
      { value: "mediocre", label: "Mediocre" },
      { value: "competent", label: "Competent" },
      { value: "skilled", label: "Skilled" },
      { value: "brilliant", label: "Brilliant" },
    ],
    required: true,
  },
  {
    id: "commander_competence_side_b",
    type: "select",
    question: "How competent is Side B's commander?",
    options: [
      { value: "incompetent", label: "Incompetent" },
      { value: "mediocre", label: "Mediocre" },
      { value: "competent", label: "Competent" },
      { value: "skilled", label: "Skilled" },
      { value: "brilliant", label: "Brilliant" },
    ],
    required: true,
  },
  {
    id: "magic_present",
    type: "boolean",
    question: "Is magic present in this world?",
    required: true,
  },
  {
    id: "magic_constraints",
    type: "textarea",
    question: "If magic is present, what are its constraints?",
    placeholder: "How powerful is magic? What can't it do? Who can use it?",
    required: false,
    conditional: { field: "magic_present", value: true },
  },
  {
    id: "narrative_outcome",
    type: "select",
    question: "What is the desired narrative outcome?",
    options: [
      { value: "decisive_victory", label: "Decisive Victory" },
      { value: "pyrrhic_victory", label: "Pyrrhic Victory" },
      { value: "stalemate", label: "Stalemate" },
      { value: "fighting_retreat", label: "Fighting Retreat" },
      { value: "rout", label: "Rout" },
      { value: "other", label: "Other" },
    ],
    required: true,
  },
  {
    id: "violence_level",
    type: "select",
    question: "What level of violence detail do you want?",
    options: [
      { value: "low", label: "Low - Minimal graphic detail" },
      { value: "medium", label: "Medium - Realistic but not gratuitous" },
      { value: "high", label: "High - Unflinching realism" },
    ],
    required: true,
  },
];

export default function InterrogationPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [coreAnswers, setCoreAnswers] = useState<CoreAnswers>({
    era: "",
    theater: "",
    why_battle_now: "",
    army_sizes: "",
    terrain_type: "",
    terrain_feature: "",
    commander_competence_side_a: "",
    commander_competence_side_b: "",
    magic_present: false,
    magic_constraints: "",
    narrative_outcome: "",
    violence_level: "",
  });
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionStatus, setSessionStatus] = useState<string | null>(null);

  useEffect(() => {
    async function checkSession() {
      try {
        const session = await getSession(sessionId);
        setSessionStatus(session.status);

        // If already past interrogation, redirect
        if (session.status === "deliberating") {
          router.push(`/session/${sessionId}/deliberation`);
          return;
        }
        if (session.status === "certified" || session.status === "failed") {
          router.push(`/session/${sessionId}/output`);
          return;
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load session");
      } finally {
        setIsLoading(false);
      }
    }

    checkSession();
  }, [sessionId, router]);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError(null);

    try {
      await submitAnswers(sessionId, coreAnswers, {});
      router.push(`/session/${sessionId}/deliberation`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit answers");
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateCoreAnswer = (questionId: string, value: string | boolean) => {
    setCoreAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <div className="animate-pulse text-war-accent">Loading interrogation form...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-16 text-center">
        <p className="text-red-500">{error}</p>
        <Button onClick={() => router.push("/")} className="mt-4">
          Return Home
        </Button>
      </div>
    );
  }

  // Filter questions based on conditionals
  const visibleQuestions = CORE_QUESTIONS.filter((q) => {
    if (!q.conditional) return true;
    const conditionValue = coreAnswers[q.conditional.field as keyof CoreAnswers];
    return conditionValue === q.conditional.value;
  });

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-war-text mb-2">Scenario Interrogation</h1>
        <p className="text-war-muted">
          Answer the following questions to provide context for expert analysis.
        </p>
      </div>

      <Card className="war-panel">
        <CardHeader>
          <CardTitle className="text-war-accent">Core Questions</CardTitle>
          <CardDescription>
            These foundational questions help establish the key parameters of your scenario.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {visibleQuestions.map((question) => (
            <QuestionField
              key={question.id}
              question={question}
              value={coreAnswers[question.id as keyof CoreAnswers]}
              onChange={(value) => updateCoreAnswer(question.id, value)}
            />
          ))}
        </CardContent>
      </Card>

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
  value: string | boolean;
  onChange: (value: string | boolean) => void;
}) {
  if (question.type === "select" && question.options) {
    return (
      <div className="space-y-2">
        <Label htmlFor={question.id} className="text-war-text">
          {question.question}
          {question.required && <span className="text-war-accent ml-1">*</span>}
        </Label>
        <Select value={value as string} onValueChange={onChange}>
          <SelectTrigger className="bg-war-bg border-war-border text-war-text">
            <SelectValue placeholder="Select an option..." />
          </SelectTrigger>
          <SelectContent>
            {question.options.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  if (question.type === "boolean") {
    return (
      <div className="flex items-center justify-between space-x-4 py-2">
        <Label htmlFor={question.id} className="text-war-text">
          {question.question}
          {question.required && <span className="text-war-accent ml-1">*</span>}
        </Label>
        <Switch
          id={question.id}
          checked={value as boolean}
          onCheckedChange={onChange}
        />
      </div>
    );
  }

  if (question.type === "textarea") {
    return (
      <div className="space-y-2">
        <Label htmlFor={question.id} className="text-war-text">
          {question.question}
          {question.required && <span className="text-war-accent ml-1">*</span>}
        </Label>
        <Textarea
          id={question.id}
          value={value as string}
          onChange={(e) => onChange(e.target.value)}
          placeholder={question.placeholder || "Enter your response..."}
          className="bg-war-bg border-war-border text-war-text placeholder:text-war-muted min-h-[100px]"
        />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={question.id} className="text-war-text">
        {question.question}
        {question.required && <span className="text-war-accent ml-1">*</span>}
      </Label>
      <Input
        id={question.id}
        value={value as string}
        onChange={(e) => onChange(e.target.value)}
        placeholder={question.placeholder || "Enter your response..."}
        className="bg-war-bg border-war-border text-war-text placeholder:text-war-muted"
      />
    </div>
  );
}
