import type { Timestamp } from "firebase/firestore";
import type { User } from "firebase/auth";

export type UserPreferences = {
  roleFocus: string;
  preferredLocation: string;
  keywords: string[];
};

export type UserProfile = {
  uid: string;
  email: string | null;
  displayName: string | null;
  fullName: string;
  photoURL: string | null;
  onboardingCompleted: boolean;
  onboardingStep: number;
  preferences: UserPreferences;
  createdAt: Timestamp | null;
  updatedAt: Timestamp | null;
};

async function getDb() {
  const { getApp } = await import("firebase/app");
  const { getFirestore } = await import("firebase/firestore");
  return getFirestore(getApp());
}

export async function getUserProfile(uid: string): Promise<UserProfile | null> {
  const { doc, getDoc } = await import("firebase/firestore");
  const db = await getDb();
  const snap = await getDoc(doc(db, "users", uid));
  if (!snap.exists()) return null;
  return snap.data() as UserProfile;
}

export async function upsertUserProfile(user: User): Promise<UserProfile | null> {
  const { doc, getDoc, setDoc, serverTimestamp } = await import("firebase/firestore");
  const db = await getDb();
  const ref = doc(db, "users", user.uid);
  const snap = await getDoc(ref);

  if (snap.exists()) {
    return snap.data() as UserProfile;
  }

  const profile: UserProfile = {
    uid: user.uid,
    email: user.email,
    displayName: user.displayName,
    fullName: user.displayName ?? "",
    photoURL: user.photoURL,
    onboardingCompleted: false,
    onboardingStep: 1,
    preferences: {
      roleFocus: "",
      preferredLocation: "",
      keywords: [],
    },
    createdAt: serverTimestamp() as Timestamp,
    updatedAt: serverTimestamp() as Timestamp,
  };

  await setDoc(ref, profile);
  return profile;
}

export async function completeUserOnboarding(
  user: User,
  data: { fullName: string; preferences: UserPreferences },
): Promise<void> {
  const { doc, setDoc, serverTimestamp } = await import("firebase/firestore");
  const db = await getDb();
  const ref = doc(db, "users", user.uid);
  await setDoc(
    ref,
    {
      fullName: data.fullName,
      preferences: data.preferences,
      onboardingCompleted: true,
      onboardingStep: 3,
      updatedAt: serverTimestamp(),
    },
    { merge: true },
  );
}
