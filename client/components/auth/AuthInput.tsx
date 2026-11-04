import { TextInput, StyleSheet } from 'react-native'

export function AuthInput(props: any) {
    return (
        <TextInput
            {...props}
            placeholderTextColor="#999"
            style={styles.input}
        />
    )
}

const styles = StyleSheet.create({
    input: {
        height: 52,
        borderRadius: 14,
        backgroundColor: '#F2F2F2',
        paddingHorizontal: 16,
        fontSize: 16,
        marginBottom: 14,
    },
})
