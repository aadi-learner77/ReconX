import { twMerge } from "tailwind-merge";

export type ClassInput = string | false | null | undefined | ClassInput[];

export function cn(...inputs: ClassInput[]): string {
  const flat: string[] = [];
  const push = (val: ClassInput) => {
    if (!val) return;
    if (Array.isArray(val)) {
      val.forEach(push);
    } else {
      flat.push(val);
    }
  };
  inputs.forEach(push);
  return twMerge(flat.join(" "));
}
