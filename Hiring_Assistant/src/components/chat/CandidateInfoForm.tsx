import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export interface CandidateInfoFormValues {
  name: string;
  email: string;
  phone: string;
  yearsExperience: string;
  desiredPosition: string;
  location: string;
  techStack: string;
}

interface CandidateInfoFormProps {
  isLoading: boolean;
  submitDisabledReason?: string | null;
  onSubmit: (values: CandidateInfoFormValues) => Promise<void>;
}

const INITIAL_VALUES: CandidateInfoFormValues = {
  name: "",
  email: "",
  phone: "",
  yearsExperience: "",
  desiredPosition: "",
  location: "",
  techStack: "",
};

export function CandidateInfoForm({ isLoading, submitDisabledReason, onSubmit }: CandidateInfoFormProps) {
  const [values, setValues] = useState<CandidateInfoFormValues>(INITIAL_VALUES);
  const [errors, setErrors] = useState<Partial<Record<keyof CandidateInfoFormValues, string>>>({});

  const isValid = useMemo(
    () => Object.values(values).every((value) => value.trim().length > 0),
    [values],
  );

  const updateField = (field: keyof CandidateInfoFormValues, value: string) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const validate = () => {
    const nextErrors: Partial<Record<keyof CandidateInfoFormValues, string>> = {};

    for (const [key, value] of Object.entries(values) as Array<[keyof CandidateInfoFormValues, string]>) {
      if (!value.trim()) {
        nextErrors[key] = "This field is required.";
      }
    }

    if (values.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(values.email.trim())) {
      nextErrors.email = "Enter a valid email address.";
    }

    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!validate()) return;
    await onSubmit(values);
  };

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-6 lg:py-8">
      <Card className="border-border/40 bg-card/70 shadow-xl shadow-slate-950/10">
        <CardHeader>
          <CardTitle className="text-2xl">Candidate Details</CardTitle>
          <CardDescription className="text-sm leading-6">
            Fill in your details here to start the interview. Once submitted, TalentScout will open 5-10 conceptual
            questions based on your stack and score each answer on technical understanding and communication.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form className="space-y-6" onSubmit={(event) => void handleSubmit(event)}>
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="candidate-name">Full Name</Label>
                <Input
                  id="candidate-name"
                  value={values.name}
                  onChange={(event) => updateField("name", event.target.value)}
                  placeholder="John Doe"
                />
                {errors.name && <p className="text-xs text-destructive">{errors.name}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="candidate-email">Email Address</Label>
                <Input
                  id="candidate-email"
                  type="email"
                  value={values.email}
                  onChange={(event) => updateField("email", event.target.value)}
                  placeholder="john@example.com"
                />
                {errors.email && <p className="text-xs text-destructive">{errors.email}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="candidate-phone">Phone Number</Label>
                <Input
                  id="candidate-phone"
                  value={values.phone}
                  onChange={(event) => updateField("phone", event.target.value)}
                  placeholder="+1 555 123 4567"
                />
                {errors.phone && <p className="text-xs text-destructive">{errors.phone}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="candidate-experience">Years of Experience</Label>
                <Input
                  id="candidate-experience"
                  value={values.yearsExperience}
                  onChange={(event) => updateField("yearsExperience", event.target.value)}
                  placeholder="3"
                />
                {errors.yearsExperience && <p className="text-xs text-destructive">{errors.yearsExperience}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="candidate-position">Desired Position(s)</Label>
                <Input
                  id="candidate-position"
                  value={values.desiredPosition}
                  onChange={(event) => updateField("desiredPosition", event.target.value)}
                  placeholder="Frontend Developer"
                />
                {errors.desiredPosition && <p className="text-xs text-destructive">{errors.desiredPosition}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="candidate-location">Current Location</Label>
                <Input
                  id="candidate-location"
                  value={values.location}
                  onChange={(event) => updateField("location", event.target.value)}
                  placeholder="Bangalore, India"
                />
                {errors.location && <p className="text-xs text-destructive">{errors.location}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="candidate-tech-stack">Tech Stack</Label>
              <Textarea
                id="candidate-tech-stack"
                value={values.techStack}
                onChange={(event) => updateField("techStack", event.target.value)}
                placeholder="React, TypeScript, Node.js, PostgreSQL, Docker"
                rows={5}
              />
              <p className="text-xs text-muted-foreground">
                Add the languages, frameworks, databases, and tools you want the interview to focus on.
              </p>
              {errors.techStack && <p className="text-xs text-destructive">{errors.techStack}</p>}
            </div>

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border/30 pt-4">
              <div className="space-y-1">
                <p className="text-sm text-muted-foreground">
                  All seven fields are required before the technical interview begins.
                </p>
                {submitDisabledReason && <p className="text-sm text-destructive">{submitDisabledReason}</p>}
              </div>
              <Button type="submit" disabled={isLoading || !isValid || Boolean(submitDisabledReason)}>
                {isLoading ? "Starting Interview..." : "Continue To Interview"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
