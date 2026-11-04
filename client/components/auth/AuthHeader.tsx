import { View, Text, StyleSheet } from 'react-native'

export function AuthHeader({ title, subtitle }: { title: string; subtitle: string }) {
    return (
        <View style={styles.container}>
            <Text style={styles.title}>{title}</Text>
            <Text style={styles.subtitle}>{subtitle}</Text>
        </View>
    )
}

const styles = StyleSheet.create({
    container: {
        marginBottom: 32,
    },
    title: {
        fontSize: 32,
        fontWeight: '700',
        color: '#111',
    },
    subtitle: {
        fontSize: 15,
        marginTop: 6,
        color: '#666',
    },
})
