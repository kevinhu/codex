import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";

export interface Entity {
  id: string;
  name: string;
  slug: string;
  description: string;
  is_primary: boolean;
  created_at: string;
}

function App() {
  const [query, setQuery] = useState<string>("");
  const [searchResults, setSearchResults] = useState<Entity[]>([]);

  useEffect(() => {
    if (query.length === 0) {
      setSearchResults([]);
      return;
    }
    try {
      axios
        .get(`http://localhost:8000/search`, {
          params: {
            query,
          },
        })
        .then((response) => {
          setSearchResults(response.data);
        });
    } catch (error) {
      console.error(error);
    }
  }, [query]);

  return (
    <div className="flex flex-col items-center">
      <div className="flex flex-col w-full max-w-screen-md space-y-2 py-12">
        <h1>Codex</h1>
        <input
          id="search"
          type="text"
          value={query}
          placeholder="Search..."
          onChange={(e) => setQuery(e.target.value)}
          className="border border-gray-300 rounded px-2 py-1"
        />
        <div className="border border-gray-300 rounded px-2 py-1 bg-gray-50 flex flex-col">
          {searchResults.map((result) => (
            <Link key={result.id} to={`/${result.id}`}>
              {result.name}
            </Link>
          ))}
          {searchResults.length === 0 && "No results"}
        </div>
      </div>
    </div>
  );
}

export default App;
