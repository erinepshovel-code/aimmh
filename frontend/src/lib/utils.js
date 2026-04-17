// "lines of code":"5","lines of commented":"0"
import { clsx } from "clsx";
import { twMerge } from "tailwind-merge"

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}
// "lines of code":"5","lines of commented":"0"
