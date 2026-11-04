import { Pressable, Text, StyleSheet } from 'react-native'

export function AuthButton({ title, onPress, disabled }: any) {
    return (
        <Pressable
            onPress={onPress}
            disabled={disabled}
            style={({ pressed }) => [
                styles.button,
                pressed && { opacity: 0.8 },
                disabled && { opacity: 0.5 },
            ]}
        >
            <Text style={styles.text}>{title}</Text>
        </Pressable>
    )
}

const styles = StyleSheet.create({
    button: {
        height: 52,
        borderRadius: 14,
        backgroundColor: '#111',
        alignItems: 'center',
        justifyContent: 'center',
        marginTop: 10,
    },
    text: {
        color: '#fff',
        fontSize: 16,
        fontWeight: '600',
    },
})
