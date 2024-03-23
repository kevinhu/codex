import { useState } from "react";
import { Toaster } from "sonner";
import MistralClient from "@mistralai/mistralai";
import { useLocalStorage } from "usehooks-ts";

function App() {
  const [apiKey, setApiKey] = useLocalStorage<string>("api_key", "");
  const [response, setResponse] = useState<string>("");

  const listModels = async () => {
    const client = new MistralClient(apiKey);

    try {
      const streamResponse = await client.chatStream({
        model: "mistral-large-latest",
        messages: [
          { role: "user", content: "What is the best French cheese?" },
        ],
      });

      setResponse("");

      for await (const chatResponse of streamResponse) {
        setResponse(
          (response) => response + chatResponse.choices[0].delta.content
        );
      }

      console.log(response);
    } catch (error) {
      console.error(error);
    }
  };

  return (
    <div className="flex flex-col items-center">
      <Toaster />
      <div className="flex flex-col w-full max-w-screen-md space-y-2 py-12">
        <label htmlFor="api_key" className="text-2xl">
          API Key
        </label>
        <input
          id="api_key"
          type="text"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1"
        />
        <button
          onClick={listModels}
          className="bg-blue-500 text-white rounded px-3 py-1"
        >
          Test endpoint
        </button>
        <div className="border border-gray-300 rounded px-2 py-1 bg-gray-50 whitespace-pre-wrap">
          {response || "What is the best French cheese?"}
        </div>
      </div>
    </div>
  );
}

export default App;
