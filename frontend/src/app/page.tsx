"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { createScenario } from "@/lib/api";

export default function LandingPage() {
  const router = useRouter();
  const [scenario, setScenario] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!scenario.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await createScenario({ scenario });
      router.push(`/session/${response.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create scenario");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="container mx-auto px-4 py-16">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-4xl md:text-5xl font-bold mb-4 text-war-text">
          Strategic Decision
          <span className="text-war-accent"> Analysis</span>
        </h1>
        <p className="text-lg text-war-muted max-w-2xl mx-auto">
          Submit your scenario for multi-expert deliberation and rigorous red team
          validation. Get certified analysis backed by diverse perspectives.
        </p>
      </div>

      {/* Input Card */}
      <Card className="max-w-3xl mx-auto war-panel war-glow">
        <CardHeader>
          <CardTitle className="text-war-accent">Describe Your Scenario</CardTitle>
          <CardDescription>
            Provide a detailed description of the situation or decision you need analyzed.
            Our expert panel will deliberate and stress-test the analysis.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Example: Our startup is considering pivoting from B2C to B2B. We have 18 months of runway, a team of 12, and our current product has 50k users but low monetization..."
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="min-h-[200px] bg-war-bg border-war-border text-war-text placeholder:text-war-muted"
          />
          {error && (
            <p className="text-red-500 text-sm">{error}</p>
          )}
          <Button
            onClick={handleSubmit}
            disabled={!scenario.trim() || isLoading}
            className="w-full bg-war-accent hover:bg-war-accentMuted text-black font-semibold"
            size="lg"
          >
            {isLoading ? "Creating Session..." : "Begin Analysis"}
          </Button>
        </CardContent>
      </Card>

      {/* Features */}
      <div className="grid md:grid-cols-3 gap-6 mt-16 max-w-5xl mx-auto">
        <FeatureCard
          title="Expert Panel"
          description="Domain experts analyze your scenario from multiple strategic angles"
          icon="E"
        />
        <FeatureCard
          title="Red Team"
          description="Adversarial review identifies weaknesses and blind spots"
          icon="R"
        />
        <FeatureCard
          title="Certification"
          description="Analysis must survive scrutiny before being certified"
          icon="C"
        />
      </div>
    </div>
  );
}

function FeatureCard({
  title,
  description,
  icon,
}: {
  title: string;
  description: string;
  icon: string;
}) {
  return (
    <div className="war-panel p-6 text-center">
      <div className="w-12 h-12 rounded-full bg-war-accent/20 flex items-center justify-center mx-auto mb-4">
        <span className="text-war-accent font-bold text-xl">{icon}</span>
      </div>
      <h3 className="font-semibold text-war-text mb-2">{title}</h3>
      <p className="text-sm text-war-muted">{description}</p>
    </div>
  );
}
