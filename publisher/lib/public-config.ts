import { getPublicConfig } from './config-policy.mjs';

export function readPublicConfig() {
  return getPublicConfig(process.env);
}
