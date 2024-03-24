import { LoaderFunctionArgs } from "react-router-dom";
import axios from "axios";
import { API_BASE_URL } from "./config";

export async function getEntity(id: string) {
  try {
    const res = await axios.get(`${API_BASE_URL}/topic`, {
      params: {
        topic_id: id,
      },
    });

    return res.data;
  } catch (error) {
    console.error(error);
  }
}

export async function loader({ params }: LoaderFunctionArgs<{ id: string }>) {
  const entity = await getEntity(decodeURIComponent(params.id || ""));
  return { entity };
}
