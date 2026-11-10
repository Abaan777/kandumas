// Non-functional requirement 4.3.2.4 (User Guidance): "The system shall include help
// or info sections to guide new users on how to read prediction results."
const FAQ = [
  {
    q: "How do I generate a forecast?",
    a: "On the Dashboard, choose a Region and a Species in the filter bar, set how many months ahead you want, then click \"Generate Prediction\". The chart will show the predicted catch on top of recent historical catch so you can compare them.",
  },
  {
    q: "What do RMSE and MAPE mean?",
    a: "Both measure how far off a model's past predictions were from what was actually caught, on months the model never saw during training. RMSE (Root Mean Squared Error) is in kilograms -- the typical size of the model's error. MAPE (Mean Absolute Percentage Error) is the same idea as a percentage. Lower is better for both. They're shown next to every forecast and on the Admin \"Model Performance\" table.",
  },
  {
    q: "The Region Map markers are colored -- what do the colors mean?",
    a: "Each region is scored by how small its best model's typical error is relative to that region's usual catch size, then colored on a gradient: red is most accurate, fading through orange and yellow, down to blue (least accurate). This is a rough, relative guide for comparing regions -- not a guarantee for any single month's forecast.",
  },
  {
    q: "Why does the forecast sometimes start a few months \"in the past\"?",
    a: "Forecasts are generated from real environmental data (sea surface temperature, wind, salinity). That data can lag a few months behind the most recent catch records for a region. When this happens the Dashboard shows a note explaining exactly how far the forecast's starting month is from the latest real catch data.",
  },
  {
    q: "What's the difference between the LSTM and Prophet models?",
    a: "Both are time-series forecasting models trained on the same historical catch and environmental data (Chapter 2, Literature Review). The system automatically picks whichever one is more accurate for a given region and species, and always labels which one produced the forecast you're looking at.",
  },
  {
    q: "Can I download a forecast to share or review offline?",
    a: "Yes -- go to Reports, choose a region, species and forecast horizon, pick CSV or PDF, and click \"Download Report\". It includes the predicted values alongside recent historical and environmental data.",
  },
  {
    q: "I'm an admin -- what do \"Refresh Datasets\" and \"Retrain Model\" do?",
    a: "\"Refresh Datasets\" re-fetches the latest catch (IOTC) and environmental (NOAA) data and rebuilds the processed feature table. \"Retrain Model\" re-trains the LSTM and Prophet models on whatever data currently exists and re-evaluates which model is best for each region/species. Both run in the background -- use \"Refresh Metrics Table\" afterwards to see the updated results.",
  },
];

export default function Help() {
  return (
    <div className="page">
      <div className="card">
        <h2>Help &amp; Guidance</h2>
        <p className="helper-text">
          Quick answers for reading forecasts and getting around the dashboard. If something here
          doesn't answer your question, ask your system administrator.
        </p>
      </div>

      <div className="card">
        {FAQ.map((item) => (
          <details key={item.q} style={{ marginBottom: "0.9rem" }}>
            <summary style={{ cursor: "pointer", fontWeight: 600 }}>{item.q}</summary>
            <p className="helper-text" style={{ marginTop: "0.5rem" }}>
              {item.a}
            </p>
          </details>
        ))}
      </div>
    </div>
  );
}
