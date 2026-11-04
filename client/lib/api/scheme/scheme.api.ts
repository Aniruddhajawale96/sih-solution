import apiClient from "../axios";

/* ================================
   Get single scheme
================================ */
interface SchemeParams {
  id: string;
}

export const getScheme = async ({ id }: SchemeParams) => {
  const res = await apiClient.get(`/scheme/${id}`);
  return res.data;
};

/* ================================
   Submit scheme application
================================ */
interface SubmitSchemeApplicationParams {
  schemeId: string;
  zipFile: {
    uri: string;
    name: string;
    type: string;
  };
}

export const submitSchemeApplication = async ({
  schemeId,
  zipFile,
}: SubmitSchemeApplicationParams) => {
  const formData = new FormData();

  formData.append("scheme_id", schemeId);
  formData.append("documents", zipFile as any);

  const res = await apiClient.post("/scheme/apply", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return res.data;
};

/* ================================
   Scheme list type
================================ */
export type SchemeShow = {
  id: string;
  title: string;
  location: string;
  description: string;
};

/* ================================
   Get schemes filtered for farmer
================================ */
export const getSchemes = async (farmerId: string): Promise<SchemeShow[]> => {
  const res = await apiClient.post("/api/v1/farmer-schemes/", {
    farmer_id: farmerId,
  });

  return res.data.schemes.map((s: any) => ({
    id: s._id,
    title: s.title,
    description: s.description,
    location: s.location,
  }));
};
