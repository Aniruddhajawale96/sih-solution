import { useAuth, useUser } from '@clerk/clerk-expo'

export type AuthData = {
  isLoading: boolean
  isLoggedIn: boolean
  userId: string | null | undefined
  user: any
}

export const useAuthContext = (): AuthData => {
  const { isLoaded, isSignedIn, userId } = useAuth()
  const { user } = useUser()

  return {
    isLoading: !isLoaded,
    isLoggedIn: !!isSignedIn,
    userId,
    user,
  }
}
