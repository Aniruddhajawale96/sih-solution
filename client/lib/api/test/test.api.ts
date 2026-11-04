import apiClient from "../axios";

interface TestParams {
  testParam: string;
}
export const getTest = async ({ testParam }: TestParams) => {
  const res = await apiClient.post(`/test`, {
    testParam,
  });

  return res.data;
};
