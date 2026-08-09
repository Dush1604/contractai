"use client";

import { useState } from "react";
import { submitProject, uploadProjectImage, ApiError, type ProjectCreatePayload } from "@/lib/api";

// Hardcoded for now — in a real embed, this would come from the contractor's
// script snippet (e.g. a data attribute), not be baked into the page.
const CONTRACTOR_ID = "351ca811-d0db-4265-a863-54bf68e99d5b";

type FormState = ProjectCreatePayload;

const initialForm: FormState = {
  title: "",
  description: "",
  homeowner_name: "",
  homeowner_email: "",
  homeowner_phone: "",
  property_location: "",
  desired_timeline: "",
  budget_range: "",
};

export default function IntakePage() {
  const [form, setForm] = useState<FormState>(initialForm);
  const [images, setImages] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<{ id: string; claimToken: string } | null>(null);

  function updateField(field: keyof FormState, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const project = await submitProject(CONTRACTOR_ID, form);

      for (const file of images) {
        try {
          await uploadProjectImage(project.id, project.claim_token, file);
        } catch {
          // Swallow individual image failures — don't block the whole
          // flow over one bad photo.
        }
      }

      setResult({ id: project.id, claimToken: project.claim_token });
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  if (result) {
    return (
      <main className="mx-auto max-w-xl px-6 py-16">
        <h1 className="text-2xl font-semibold text-green-700">Request received</h1>
        <p className="mt-3 text-gray-700">
          We&apos;re analyzing your project and will follow up shortly. Save this link to check
          your status:
        </p>
        <code className="mt-4 block break-all rounded bg-gray-100 p-3 text-sm">
          {`${window.location.origin}/status/${result.id}?claim_token=${result.claimToken}`}
        </code>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-xl px-6 py-16">
      <h1 className="text-2xl font-semibold">Request an Estimate</h1>
      <p className="mt-2 text-gray-600">
        Tell us about your project and we&apos;ll get back to you with next steps.
      </p>

      <form onSubmit={handleSubmit} className="mt-8 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700">Project title *</label>
          <input
            required
            minLength={3}
            maxLength={200}
            value={form.title}
            onChange={(e) => updateField("title", e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            placeholder="Backyard deck replacement"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Description *</label>
          <textarea
            required
            minLength={10}
            maxLength={5000}
            value={form.description}
            onChange={(e) => updateField("description", e.target.value)}
            rows={4}
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            placeholder="I want to build a 12x16 backyard deck..."
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Photos</label>
          <input
            type="file"
            multiple
            accept="image/*"
            onChange={(e) => setImages(Array.from(e.target.files ?? []))}
            className="mt-1 w-full text-sm"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Your name *</label>
            <input
              required
              value={form.homeowner_name}
              onChange={(e) => updateField("homeowner_name", e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Email *</label>
            <input
              required
              type="email"
              value={form.homeowner_email}
              onChange={(e) => updateField("homeowner_email", e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
            />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Phone</label>
          <input
            value={form.homeowner_phone}
            onChange={(e) => updateField("homeowner_phone", e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Property location</label>
          <input
            value={form.property_location}
            onChange={(e) => updateField("property_location", e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Desired timeline</label>
            <input
              value={form.desired_timeline}
              onChange={(e) => updateField("desired_timeline", e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              placeholder="Within 2 months"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Budget range</label>
            <input
              value={form.budget_range}
              onChange={(e) => updateField("budget_range", e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2"
              placeholder="$6,000–$10,000"
            />
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded bg-blue-600 px-4 py-2 font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {submitting ? "Submitting..." : "Request an Estimate"}
        </button>
      </form>
    </main>
  );
}
