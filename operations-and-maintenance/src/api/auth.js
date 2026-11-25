import { post, postForm } from './request.js'

/** POST /auth/login — application/x-www-form-urlencoded */
export function login(username, password) {
  return postForm('/auth/login', { username, password })
}

/** POST /auth/register — application/json */
export function register(username, password, role, regKey) {
  return post('/auth/register', {
    username,
    password,
    role,
    reg_key: regKey,
  })
}
