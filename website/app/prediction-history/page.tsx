import type { Metadata } from "next";
import PredictionHistory from "@/features/prediction-history/components/PredictionHistory";
import { getPredictionHistoryData } from "@/lib/prediction-history-data";

export const metadata: Metadata = {
  title: "Prediction History - FIFA 2026 Predictor",
  description:
    "Explore genuine archived matchday forecasts and see how FIFA 2026 championship probabilities changed as confirmed results arrived.",
};

export default function PredictionHistoryPage() {
  return <PredictionHistory data={getPredictionHistoryData()} />;
}
