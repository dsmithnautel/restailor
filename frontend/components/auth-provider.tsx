"use client";

import type { User } from "firebase/auth";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { getFirebaseAuth, isFirebaseConfigured } from "@/lib/firebase/client";
import {
  getUserProfile,
  type UserProfile,
  upsertUserProfile,
} from "@/lib/firebase/user-profile";

type AuthContextValue = {
  user: User | null;
  profile: UserProfile | null;
  loading: boolean;
  profileLoading: boolean;
  configured: boolean;
  refreshProfile: () => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  signOutUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [profileLoading, setProfileLoading] = useState(false);

  const refreshProfile = useCallback(async () => {
    if (!isFirebaseConfigured) return;

    const auth = await getFirebaseAuth();
    const activeUser = auth.currentUser;
    if (!activeUser) {
      setProfile(null);
      return;
    }

    const nextProfile = await getUserProfile(activeUser.uid);
    setProfile(nextProfile);
  }, []);

  useEffect(() => {
    if (!isFirebaseConfigured) {
      setLoading(false);
      setProfileLoading(false);
      return;
    }

    let unsubscribe: (() => void) | undefined;

    (async () => {
      const { onAuthStateChanged } = await import("firebase/auth");
      const auth = await getFirebaseAuth();
      unsubscribe = onAuthStateChanged(auth, async (nextUser) => {
        setUser(nextUser);
        setLoading(false);

        if (!nextUser) {
          setProfile(null);
          setProfileLoading(false);
          return;
        }

        setProfileLoading(true);

        try {
          const ensuredProfile = await upsertUserProfile(nextUser);
          if (ensuredProfile) {
            setProfile(ensuredProfile);
          }

          const freshProfile = await getUserProfile(nextUser.uid);
          if (freshProfile) {
            setProfile(freshProfile);
          }
        } catch (error) {
          console.error("Failed to sync user profile:", error);
        } finally {
          setProfileLoading(false);
        }
      });
    })();

    return () => {
      unsubscribe?.();
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      profile,
      loading,
      profileLoading,
      configured: isFirebaseConfigured,
      refreshProfile,
      signInWithGoogle: async () => {
        if (!isFirebaseConfigured) {
          throw new Error("Firebase is not configured.");
        }
        const { GoogleAuthProvider, signInWithPopup } = await import("firebase/auth");
        const auth = await getFirebaseAuth();
        const provider = new GoogleAuthProvider();
        provider.setCustomParameters({ prompt: "select_account" });
        const credential = await signInWithPopup(auth, provider);
        const ensuredProfile = await upsertUserProfile(credential.user);
        if (ensuredProfile) {
          setProfile(ensuredProfile);
        }
        await refreshProfile();
      },
      signOutUser: async () => {
        if (!isFirebaseConfigured) return;
        const { signOut } = await import("firebase/auth");
        const auth = await getFirebaseAuth();
        await signOut(auth);
        setProfile(null);
      },
    }),
    [user, profile, loading, profileLoading, refreshProfile],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
